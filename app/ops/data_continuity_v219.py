from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CURRENT_DB = ROOT / "data" / "products.db"
MARKER = ROOT / ".runtime" / "data_continuity_v219.json"



def _quick_check(path: Path) -> bool:
    if not path.exists():
        return False
    conn = None
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
        rows = [str(row[0]) for row in conn.execute("PRAGMA quick_check(1)").fetchall()]
        return bool(rows) and all(row.lower() == "ok" for row in rows)
    except sqlite3.Error:
        return False
    finally:
        if conn is not None:
            conn.close()

def _full_integrity_check(path: Path) -> bool:
    if not path.exists():
        return False
    conn = None
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=15)
        rows = [str(row[0]) for row in conn.execute("PRAGMA integrity_check").fetchall()]
        return bool(rows) and all(row.lower() == "ok" for row in rows)
    except sqlite3.Error:
        return False
    finally:
        if conn is not None:
            conn.close()


def _table_count(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    try:
        sql = f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else "")
        return int(conn.execute(sql).fetchone()[0] or 0)
    except sqlite3.Error:
        return 0


def _db_metrics(path: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "path": str(path),
        "active_global_offers": 0,
        "global_offers": 0,
        "raw_products": 0,
        "product_offers": 0,
        "global_price_history": 0,
        "favorites": 0,
        "price_history": 0,
        "size": path.stat().st_size if path.exists() else 0,
        "mtime": path.stat().st_mtime if path.exists() else 0.0,
    }
    if not path.exists():
        return metrics
    if not _quick_check(path):
        metrics["invalid"] = True
        metrics["integrity"] = "FAILED_QUICK_CHECK"
        return metrics
    if not _full_integrity_check(path):
        metrics["invalid"] = True
        metrics["integrity"] = "FAILED_FULL_INTEGRITY_CHECK"
        return metrics
    metrics["integrity"] = "FULL_OK"
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
        try:
            metrics["active_global_offers"] = _table_count(
                conn,
                "global_offers",
                "is_active = 1 AND is_hidden = 0 AND lifecycle_status = 'ACTIVE'",
            )
            metrics["global_offers"] = _table_count(conn, "global_offers")
            metrics["raw_products"] = _table_count(conn, "raw_products")
            metrics["product_offers"] = _table_count(conn, "product_offers")
            metrics["global_price_history"] = _table_count(conn, "global_offer_price_history")
            metrics["favorites"] = _table_count(conn, "favorites")
            metrics["price_history"] = _table_count(conn, "price_history")
        finally:
            conn.close()
    except sqlite3.Error:
        metrics["invalid"] = True
    return metrics


def _score(metrics: dict[str, Any]) -> tuple[int, ...]:
    # Öncelik canlı katalog ve kullanıcı verisinin korunmasıdır. Dosya zamanı yalnızca
    # eşit veri hacminde son karar verici olarak kullanılır.
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
    candidates: set[Path] = set()
    bases = [ROOT.parent, ROOT.parent.parent]
    patterns = (
        "FirsatAI-v*/data/products.db",
        "FirsatAI-v*/FirsatAI-v*/data/products.db",
        "firsatai_v*/data/products.db",
        "firsatai_v*/firsatai_v*/data/products.db",
    )
    for base in bases:
        if not base.exists():
            continue
        for pattern in patterns:
            for path in base.glob(pattern):
                try:
                    resolved = path.resolve()
                except OSError:
                    continue
                if resolved != CURRENT_DB.resolve() and resolved.is_file():
                    candidates.add(resolved)
    return sorted(candidates)


def _sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".v219tmp")
    for stale in (tmp, Path(str(tmp) + "-wal"), Path(str(tmp) + "-shm")):
        if stale.exists():
            stale.unlink()

    if not _full_integrity_check(source):
        raise RuntimeError(f"Continuity source full integrity check gecemedi: {source}")

    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True, timeout=20)
    dst = sqlite3.connect(tmp.as_posix(), timeout=20)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()

    if not _full_integrity_check(tmp):
        raise RuntimeError(f"Continuity temp backup full integrity check gecemedi: {tmp}")

    for sidecar in (Path(str(destination) + "-wal"), Path(str(destination) + "-shm")):
        if sidecar.exists():
            sidecar.unlink()

    tmp.replace(destination)

    if not _full_integrity_check(destination):
        raise RuntimeError(f"Continuity destination full integrity check gecemedi: {destination}")


def run() -> dict[str, Any]:
    CURRENT_DB.parent.mkdir(parents=True, exist_ok=True)
    current = _db_metrics(CURRENT_DB)
    candidates = [_db_metrics(p) for p in _candidate_paths()]
    candidates = [m for m in candidates if not m.get("invalid")]
    richest = max(candidates, key=_score, default=None)

    result: dict[str, Any] = {
        "engine": "FIRSATAI_DATA_CONTINUITY",
        "version": "21.9.0",
        "current_before": current,
        "candidate_count": len(candidates),
        "imported": False,
        "source": None,
    }

    if richest is not None and _score(richest) > _score(current):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if CURRENT_DB.exists():
            backup = ROOT / "data" / "backups" / f"products-pre-v219-{timestamp}.db"
            _sqlite_backup(CURRENT_DB, backup)
            result["backup"] = str(backup)
        _sqlite_backup(Path(richest["path"]), CURRENT_DB)
        result["imported"] = True
        result["source"] = richest
        result["current_after"] = _db_metrics(CURRENT_DB)

    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    outcome = run()
    if outcome.get("imported"):
        src = outcome.get("source", {})
        print("V21.9 veri devamliligi: daha zengin önceki veritabanı devralındı.")
        print("Kaynak:", src.get("path"))
        print("Aktif GlobalOffer:", src.get("active_global_offers"))
    else:
        print("V21.9 veri devamliligi: mevcut veritabanı korunuyor; daha zengin önceki DB bulunmadı.")
