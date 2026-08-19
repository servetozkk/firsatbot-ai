from __future__ import annotations

import sqlite3
from pathlib import Path

from app.services.price_integrity_math_v219 import decide_price_integrity

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "products.db"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


conn = sqlite3.connect(DB)
try:
    prices = [
        float(row[0])
        for row in conn.execute(
            "SELECT current_price FROM global_offers "
            "WHERE global_product_id=125 AND is_active=1 AND is_hidden=0 "
            "AND lifecycle_status='ACTIVE' AND current_price>0 ORDER BY current_price"
        ).fetchall()
    ]
finally:
    conn.close()

require(len(prices) >= 2, "global product 125 için en az iki gerçek emsal fiyat mevcut")
verdict = decide_price_integrity(candidate_price=1500.0, evidence_prices=prices[:2])
require(not verdict.trusted and verdict.status == "QUARANTINED", "1500 TL güçlü emsaller karşısında karantinaya alınır")
require(verdict.reference_price is not None and verdict.reference_price > 20000, "karantina referansı gerçek laptop fiyat bandında")

parser = (ROOT / "app" / "parsers" / "teknosa_parser.py").read_text(encoding="utf-8")
require("_dominant_laptop_price_from_text" in parser, "Teknosa baskın sayfa fiyatı koruması mevcut")
require("Satıcıya\\s*Sor" in parser, "Teknosa seller metni temizliği mevcut")

core = (ROOT / "app" / "services" / "price_comparison_core_v21_service.py").read_text(encoding="utf-8")
require("quarantined_rows" in core and "QUARANTINED" in core, "karantinalı teklifler serving havuzundan ayrılıyor")

reconcile = (ROOT / "app" / "services" / "catalog_reconciliation_service.py").read_text(encoding="utf-8")
require("evaluate_price_candidate" in reconcile, "fiyat bütünlüğü ingestion pipeline içinde")
require('notin_(("MISSING", "QUARANTINED"))' in reconcile, "dedupe karantinalı düşük fiyatı yeniden aktifleştirmiyor")

main = (ROOT / "main.py").read_text(encoding="utf-8")
require('/api/runtime-identity/v219' in main, "v21.9 runtime identity endpoint mevcut")
require('audit_all_prices()' in main, "startup mevcut katalog fiyatlarını denetliyor")
print("V21.9 smoke test tamamlandı.")
