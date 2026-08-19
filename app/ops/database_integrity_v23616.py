from __future__ import annotations

import json
import shutil
import sys
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

# Bu dosya hem `python -m app.ops...` hem de dogrudan
# `python app\ops\database_integrity_v23616.py` ile calisabilsin.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ops.data_continuity_v236284 import (
    _candidate_paths as _continuity_candidate_paths_v236284,
    _metrics as _continuity_metrics_v236284,
    _select_best_candidate as _continuity_select_best_v236284,
)

CURRENT_DB = ROOT / "data" / "products.db"
STATE = ROOT / ".runtime" / "database_integrity_v23616.json"
BACKUP_DIR = ROOT / "data" / "backups"


def _check(path: Path, *, full: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
        "ok": False,
        "check": "integrity_check" if full else "quick_check",
        "message": "missing",
    }
    if not path.exists():
        return result

    conn = None
    try:
        uri = f"file:{path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10)
        pragma = "PRAGMA integrity_check" if full else "PRAGMA quick_check(1)"
        rows = [str(row[0]) for row in conn.execute(pragma).fetchall()]
        ok = bool(rows) and all(row.lower() == "ok" for row in rows)
        result["ok"] = ok
        result["message"] = "ok" if ok else " | ".join(rows[:20])
    except sqlite3.Error as exc:
        result["message"] = f"{type(exc).__name__}: {exc}"
    finally:
        if conn is not None:
            conn.close()
    return result


def _count(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    try:
        sql = f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else "")
        return int(conn.execute(sql).fetchone()[0] or 0)
    except sqlite3.Error:
        return 0


def _metrics(path: Path) -> dict[str, Any]:
    check = _check(path)
    metrics: dict[str, Any] = {
        **check,
        "active_global_offers": 0,
        "global_offers": 0,
        "raw_products": 0,
        "product_offers": 0,
        "global_price_history": 0,
        "favorites": 0,
        "price_history": 0,
        "mtime": path.stat().st_mtime if path.exists() else 0.0,
    }
    if not check["ok"]:
        return metrics

    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        metrics["active_global_offers"] = _count(
            conn,
            "global_offers",
            "is_active = 1 AND is_hidden = 0 AND lifecycle_status = 'ACTIVE'",
        )
        metrics["global_offers"] = _count(conn, "global_offers")
        metrics["raw_products"] = _count(conn, "raw_products")
        metrics["product_offers"] = _count(conn, "product_offers")
        metrics["global_price_history"] = _count(conn, "global_offer_price_history")
        metrics["favorites"] = _count(conn, "favorites")
        metrics["price_history"] = _count(conn, "price_history")
    finally:
        conn.close()
    return metrics


def _score(metrics: dict[str, Any]) -> tuple[int, ...]:
    return (
        int(metrics.get("active_global_offers", 0)),
        int(metrics.get("global_offers", 0)),
        int(metrics.get("raw_products", 0)),
        int(metrics.get("product_offers", 0)),
        int(metrics.get("global_price_history", 0)),
        int(metrics.get("favorites", 0)),
        int(metrics.get("price_history", 0)),
        int(metrics.get("size", 0)),
        int(metrics.get("mtime", 0)),
    )


def _candidate_paths() -> list[Path]:
    return _continuity_candidate_paths_v236284()


def _raw_quarantine(path: Path, timestamp: str) -> list[str]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        if not source.exists():
            continue
        suffix = source.name.replace("products.db", "")
        target = BACKUP_DIR / f"products-CORRUPT-v23616-{timestamp}{suffix}.db"
        shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def _verified_sqlite_copy(source: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(".v23616-recovery.tmp.db")
    for path in (tmp, Path(str(tmp) + "-wal"), Path(str(tmp) + "-shm")):
        if path.exists():
            path.unlink()

    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True, timeout=20)
    dst = sqlite3.connect(str(tmp), timeout=20)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()

    validation = _check(tmp, full=True)
    if not validation["ok"]:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise RuntimeError(
            "Recovery kopyasi integrity_check gecemedi: "
            + str(validation.get("message"))
        )

    # Remove stale sidecars before atomic replacement.
    for sidecar in (Path(str(destination) + "-wal"), Path(str(destination) + "-shm")):
        if sidecar.exists():
            sidecar.unlink()
    tmp.replace(destination)
    return validation


def run() -> dict[str, Any]:
    CURRENT_DB.parent.mkdir(parents=True, exist_ok=True)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    current_before = _metrics(CURRENT_DB)
    candidate_paths = _candidate_paths()
    candidates = [_metrics(path) for path in candidate_paths]
    healthy_candidates = [item for item in candidates if item.get("ok")]
    continuity_candidates = [_continuity_metrics_v236284(path) for path in candidate_paths]
    richest_continuity = _continuity_select_best_v236284(continuity_candidates)
    richest = None
    if richest_continuity is not None:
        richest_path = str(richest_continuity.get("path") or "")
        richest = next((item for item in healthy_candidates if str(item.get("path") or "") == richest_path), None)
    if richest is None:
        richest = max(healthy_candidates, key=_score, default=None)

    result: dict[str, Any] = {
        "engine": "FIRSATAI_DATABASE_INTEGRITY",
        "version": "23.62.16",
        "current_before": current_before,
        "healthy_candidate_count": len(healthy_candidates),
        "candidate_count": len(candidates),
        "recovered": False,
        "recovery_source": None,
        "quarantine_files": [],
        "startup_allowed": False,
    }

    if current_before.get("ok"):
        # Current database is healthy. Run full integrity check once per startup
        # before permitting writes.
        full = _check(CURRENT_DB, full=True)
        result["current_full_check"] = full
        result["startup_allowed"] = bool(full.get("ok"))
    else:
        result["quarantine_files"] = _raw_quarantine(CURRENT_DB, timestamp)
        if richest is None:
            result["failure"] = (
                "Aktif products.db bozuk ve integrity check gecen onceki bir DB bulunamadi."
            )
        else:
            source = Path(str(richest["path"]))
            result["recovery_source"] = richest
            _verified_sqlite_copy(source, CURRENT_DB)
            result["recovered"] = True
            result["current_after"] = _metrics(CURRENT_DB)
            result["current_full_check"] = _check(CURRENT_DB, full=True)
            result["startup_allowed"] = bool(
                result["current_after"].get("ok")
                and result["current_full_check"].get("ok")
            )

    STATE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    outcome = run()
    if outcome.get("recovered"):
        src = outcome.get("recovery_source") or {}
        print("V23.62.16 DB RECOVERY: bozuk aktif veritabani karantinaya alindi.")
        print("Recovery kaynagi:", src.get("path"))
        print("Aktif GlobalOffer:", src.get("active_global_offers"))
    elif outcome.get("startup_allowed"):
        print("V23.62.16 DB INTEGRITY: products.db saglikli; startup serbest.")
    else:
        print("V23.62.16 DB INTEGRITY FAILED:")
        print(outcome.get("failure") or outcome.get("current_full_check"))
        raise SystemExit(2)
