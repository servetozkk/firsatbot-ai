from __future__ import annotations
from pathlib import Path
import json
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_INDEXES = {
    "ix_product_offers_group_active_hidden_price",
    "ix_product_offers_store_active_checked",
    "ix_offer_price_history_offer_created",
    "ix_product_groups_category_brand",
}

def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main() -> int:
    report = ROOT / "data" / "reports" / "v11_5_0_performance_scale_report.json"
    ok(report.exists(), "performans raporu mevcut")
    data = json.loads(report.read_text(encoding="utf-8-sig"))
    ok(data.get("integrity") == "ok", "SQLite integrity başarılı")
    ok(data.get("foreign_key_violations") == 0, "foreign key ihlali yok")
    installed = set(data.get("installed_indexes") or [])
    ok(REQUIRED_INDEXES.issubset(installed), "4 bileşik indeks raporda mevcut")
    synthetic = data.get("synthetic_scale") or {}
    ok(int(synthetic.get("rows_per_table") or 0) >= 100000, "100 bin satırlık sentetik test çalıştı")

    conn = sqlite3.connect(ROOT / "data" / "products.db")
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    fk = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    conn.close()
    ok(integrity == "ok", "canlı veritabanı integrity başarılı")
    ok(fk == 0, "canlı veritabanında foreign key ihlali yok")
    for name in sorted(REQUIRED_INDEXES):
        ok(name in names, f"{name} mevcut")
    print("\nv12 performans regresyonu başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
