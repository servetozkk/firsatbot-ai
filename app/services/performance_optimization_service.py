from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "products.db"
REPORT_PATH = ROOT / "data" / "reports" / "v13_7_0_performance_optimization.json"
ENGINE_VERSION = "13.7.0"

INDEXES: dict[str, str] = {
    "ix_v1370_product_groups_created_category_brand": (
        "CREATE INDEX IF NOT EXISTS ix_v1370_product_groups_created_category_brand "
        "ON product_groups(created_at DESC, category, brand)"
    ),
    "ix_v1370_offers_active_hidden_created": (
        "CREATE INDEX IF NOT EXISTS ix_v1370_offers_active_hidden_created "
        "ON product_offers(is_active, is_hidden, created_at DESC)"
    ),
    "ix_v1370_offers_price_drop": (
        "CREATE INDEX IF NOT EXISTS ix_v1370_offers_price_drop "
        "ON product_offers(is_active, is_hidden, old_price, current_price)"
    ),
    "ix_v1370_offers_stock_price": (
        "CREATE INDEX IF NOT EXISTS ix_v1370_offers_stock_price "
        "ON product_offers(availability, is_active, is_hidden, current_price)"
    ),
    "ix_v1370_offers_group_store_price": (
        "CREATE INDEX IF NOT EXISTS ix_v1370_offers_group_store_price "
        "ON product_offers(group_id, is_active, is_hidden, store_id, current_price)"
    ),
}


def existing_indexes(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}


def index_status(db_path: Path = DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        return {"version": ENGINE_VERSION, "ready": False, "error": "database_not_found"}
    with sqlite3.connect(str(db_path)) as conn:
        current = existing_indexes(conn)
        installed = sorted(name for name in INDEXES if name in current)
        missing = sorted(name for name in INDEXES if name not in current)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    return {
        "version": ENGINE_VERSION,
        "ready": integrity == "ok" and foreign_keys == 0 and not missing,
        "integrity": integrity,
        "foreign_key_violations": foreign_keys,
        "installed_indexes": installed,
        "missing_indexes": missing,
        "index_count": len(installed),
        "expected_index_count": len(INDEXES),
    }


def load_report() -> dict[str, Any]:
    if not REPORT_PATH.exists():
        return {"version": ENGINE_VERSION, "status": "REPORT_NOT_GENERATED", **index_status()}
    try:
        data = json.loads(REPORT_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"version": ENGINE_VERSION, "status": "REPORT_INVALID", **index_status()}
    data["current_index_status"] = index_status()
    return data
