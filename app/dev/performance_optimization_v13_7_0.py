from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import time
from datetime import datetime
from pathlib import Path

from app.services.performance_optimization_service import DB_PATH, ENGINE_VERSION, INDEXES, REPORT_PATH, existing_indexes

ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "data" / "backups" / "performance_v13_7_0"

QUERIES = {
    "new_products": (
        "SELECT id, canonical_name, category, brand, created_at FROM product_groups "
        "ORDER BY created_at DESC LIMIT 100",
        (),
    ),
    "category_products": (
        "SELECT id, canonical_name, brand, created_at FROM product_groups "
        "WHERE category=? ORDER BY created_at DESC LIMIT 100",
        ("Laptop",),
    ),
    "price_drops": (
        "SELECT id, group_id, current_price, old_price FROM product_offers "
        "WHERE is_active=1 AND is_hidden=0 AND old_price>current_price AND current_price>0 "
        "ORDER BY ((old_price-current_price)/old_price) DESC LIMIT 100",
        (),
    ),
    "stock_offers": (
        "SELECT id, group_id, current_price FROM product_offers "
        "WHERE availability=? AND is_active=1 AND is_hidden=0 AND current_price>0 "
        "ORDER BY current_price ASC LIMIT 100",
        ("IN_STOCK",),
    ),
    "group_offers": (
        "SELECT store_id, current_price, availability FROM product_offers "
        "WHERE group_id=? AND is_active=1 AND is_hidden=0 ORDER BY current_price ASC LIMIT 50",
        (1,),
    ),
}


def choose_params(conn: sqlite3.Connection) -> dict[str, tuple]:
    params = {name: values for name, (_, values) in QUERIES.items()}
    row = conn.execute("SELECT category FROM product_groups WHERE category IS NOT NULL AND category<>'' LIMIT 1").fetchone()
    if row:
        params["category_products"] = (row[0],)
    row = conn.execute("SELECT group_id FROM product_offers GROUP BY group_id ORDER BY COUNT(*) DESC LIMIT 1").fetchone()
    if row:
        params["group_offers"] = (row[0],)
    row = conn.execute("SELECT availability FROM product_offers WHERE availability IS NOT NULL AND availability<>'' LIMIT 1").fetchone()
    if row:
        params["stock_offers"] = (row[0],)
    return params


def benchmark(conn: sqlite3.Connection, sql: str, params: tuple, rounds: int = 120) -> dict[str, float]:
    samples: list[float] = []
    for _ in range(rounds):
        started = time.perf_counter_ns()
        conn.execute(sql, params).fetchall()
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
    samples.sort()
    p95_index = max(0, min(len(samples) - 1, int(len(samples) * 0.95) - 1))
    return {
        "median_ms": round(statistics.median(samples), 4),
        "p95_ms": round(samples[p95_index], 4),
        "max_ms": round(max(samples), 4),
    }


def plans(conn: sqlite3.Connection, params: dict[str, tuple]) -> dict[str, list[str]]:
    return {
        name: [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params[name]).fetchall()]
        for name, (sql, _) in QUERIES.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-indexes", action="store_true")
    parser.add_argument("--rounds", type=int, default=120)
    args = parser.parse_args()
    if not DB_PATH.exists():
        raise SystemExit(f"Veritabani bulunamadi: {DB_PATH}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")
    integrity_before = conn.execute("PRAGMA integrity_check").fetchone()[0]
    fk_before = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    params = choose_params(conn)
    before = {name: benchmark(conn, sql, params[name], max(20, args.rounds)) for name, (sql, _) in QUERIES.items()}
    plans_before = plans(conn, params)
    current = existing_indexes(conn)
    missing_before = [name for name in INDEXES if name not in current]
    backup_path: Path | None = None

    if args.apply_indexes and missing_before:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"products_before_v13_7_0_{stamp}.db"
        backup_conn = sqlite3.connect(str(backup_path))
        conn.backup(backup_conn)
        backup_conn.close()
        for name in missing_before:
            conn.execute(INDEXES[name])
        conn.commit()
        conn.execute("ANALYZE")
        conn.execute("PRAGMA optimize")
        conn.commit()

    after = {name: benchmark(conn, sql, params[name], max(20, args.rounds)) for name, (sql, _) in QUERIES.items()}
    plans_after = plans(conn, params)
    current_after = existing_indexes(conn)
    installed = [name for name in INDEXES if name in current_after]
    missing_after = [name for name in INDEXES if name not in current_after]
    integrity_after = conn.execute("PRAGMA integrity_check").fetchone()[0]
    fk_after = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    counts = {}
    for table in ("product_groups", "product_offers", "offer_price_history", "stores"):
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()

    improvements = {}
    for name in QUERIES:
        old = before[name]["median_ms"]
        new = after[name]["median_ms"]
        improvements[name] = round(((old - new) / old) * 100, 2) if old else 0.0

    slowest_p95 = max(item["p95_ms"] for item in after.values())
    ready = integrity_after == "ok" and fk_after == 0 and not missing_after and slowest_p95 < 250
    status = "PERFORMANCE_OPTIMIZED" if ready else "PERFORMANCE_READY_WITH_WARNINGS"
    report = {
        "version": ENGINE_VERSION,
        "status": status,
        "database_changed": bool(args.apply_indexes and missing_before),
        "backup": str(backup_path) if backup_path else None,
        "integrity_before": integrity_before,
        "integrity_after": integrity_after,
        "foreign_key_violations_before": fk_before,
        "foreign_key_violations_after": fk_after,
        "counts": counts,
        "missing_indexes_before": missing_before,
        "installed_indexes": installed,
        "missing_indexes_after": missing_after,
        "benchmarks_before": before,
        "benchmarks_after": after,
        "improvement_percent": improvements,
        "query_plans_before": plans_before,
        "query_plans_after": plans_after,
        "slowest_p95_ms": slowest_p95,
        "generated_at": datetime.now().isoformat(),
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK  SQLite integrity: {integrity_after}")
    print(f"OK  Foreign key ihlali: {fk_after}")
    print(f"OK  Performans indeksi: {len(installed)}/{len(INDEXES)}")
    for name, result in after.items():
        print(f"BILGI  {name}: median={result['median_ms']} ms, p95={result['p95_ms']} ms")
    print(f"BILGI  En yavas p95: {slowest_p95} ms")
    print(f"DURUM: {status}")
    print(f"RAPOR: {REPORT_PATH}")
    if backup_path:
        print(f"DB YEDEGI: {backup_path}")
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
