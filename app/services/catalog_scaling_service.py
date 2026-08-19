from __future__ import annotations

import base64
import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable

ENGINE_VERSION = "13.7.3"
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "products.db"
REPORT_PATH = ROOT / "data" / "reports" / "v13_7_3_catalog_scaling.json"
MAX_LIMIT = 200
DEFAULT_LIMIT = 50


def encode_cursor(product_id: int) -> str:
    raw = json.dumps({"id": int(product_id)}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        value = int(payload.get("id", 0))
        return max(0, value)
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Gecersiz cursor")


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path or DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def list_products_cursor(*, cursor: str | None = None, limit: int = DEFAULT_LIMIT, category: str | None = None, db_path: Path | None = None) -> dict[str, Any]:
    limit = max(1, min(int(limit), MAX_LIMIT))
    last_id = decode_cursor(cursor)
    params: list[Any] = [last_id]
    where = ["gp.id > ?", "gp.status = 'active'"]
    if category:
        where.append("lower(coalesce(gp.category,'')) = lower(?)")
        params.append(category.strip())
    params.append(limit + 1)
    sql = f"""
        SELECT gp.id, gp.identity_key, gp.canonical_name, gp.normalized_brand AS brand,
               gp.category, gp.primary_image, gp.active_offer_count,
               MIN(CASE WHEN go.is_active=1 AND go.is_hidden=0 AND go.current_price>0
                        THEN go.current_price + COALESCE(go.shipping_price,0) END) AS min_price,
               COUNT(DISTINCT CASE WHEN go.is_active=1 AND go.is_hidden=0 THEN go.store_code END) AS store_count,
               gp.updated_at
        FROM global_products gp
        LEFT JOIN global_offers go ON go.global_product_id=gp.id
        WHERE {' AND '.join(where)}
        GROUP BY gp.id
        ORDER BY gp.id ASC
        LIMIT ?
    """
    started = time.perf_counter()
    with closing(_connect(db_path)) as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    elapsed_ms = round((time.perf_counter() - started) * 1000, 4)
    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = encode_cursor(items[-1]["id"]) if has_more and items else None
    return {
        "engine_version": ENGINE_VERSION,
        "pagination": "keyset",
        "items": items,
        "count": len(items),
        "has_more": has_more,
        "next_cursor": next_cursor,
        "query_ms": elapsed_ms,
        "read_only": True,
    }


def iter_products_ndjson(*, cursor: str | None = None, limit: int = DEFAULT_LIMIT, category: str | None = None, db_path: Path | None = None) -> Iterable[bytes]:
    payload = list_products_cursor(cursor=cursor, limit=limit, category=category, db_path=db_path)
    for item in payload["items"]:
        yield (json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    yield (json.dumps({"next_cursor": payload["next_cursor"], "has_more": payload["has_more"]}, separators=(",", ":")) + "\n").encode("utf-8")


def catalog_health(db_path: Path | None = None) -> dict[str, Any]:
    path = db_path or DB_PATH
    started = time.perf_counter()
    with closing(_connect(path)) as conn:
        product_count = conn.execute("SELECT COUNT(*) FROM global_products").fetchone()[0]
        active_products = conn.execute("SELECT COUNT(*) FROM global_products WHERE status='active'").fetchone()[0]
        offer_count = conn.execute("SELECT COUNT(*) FROM global_offers").fetchone()[0]
        active_offers = conn.execute("SELECT COUNT(*) FROM global_offers WHERE is_active=1 AND is_hidden=0").fetchone()[0]
        stores = conn.execute("SELECT COUNT(DISTINCT store_code) FROM global_offers WHERE is_active=1 AND is_hidden=0").fetchone()[0]
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk_violations = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        index_names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    db_size = path.stat().st_size if path.exists() else 0
    elapsed_ms = round((time.perf_counter() - started) * 1000, 4)
    required = {"ix_global_products_status_id", "ix_global_offers_product_active_price"}
    return {
        "engine_version": ENGINE_VERSION,
        "status": "CATALOG_SCALING_READY" if integrity == "ok" and fk_violations == 0 else "CATALOG_SCALING_WARNING",
        "product_count": product_count,
        "active_product_count": active_products,
        "offer_count": offer_count,
        "active_offer_count": active_offers,
        "active_store_count": stores,
        "average_offers_per_product": round(active_offers / active_products, 3) if active_products else 0,
        "database_bytes": db_size,
        "sqlite_integrity": integrity,
        "foreign_key_violations": fk_violations,
        "required_indexes": sorted(required),
        "installed_required_indexes": sorted(required & index_names),
        "health_query_ms": elapsed_ms,
        "pagination": {"type": "keyset", "max_limit": MAX_LIMIT, "streaming": True},
        "read_only": True,
    }


def write_report(db_path: Path | None = None, report_path: Path | None = None) -> dict[str, Any]:
    health = catalog_health(db_path)
    sample = list_products_cursor(limit=25, db_path=db_path)
    health["sample_query_ms"] = sample["query_ms"]
    health["sample_count"] = sample["count"]
    target = report_path or REPORT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8")
    return health
