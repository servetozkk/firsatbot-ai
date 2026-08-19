from pathlib import Path
from types import SimpleNamespace

from app.services.bulk_catalog_service import catalog_status, init_bulk_catalog_schema, stage_item

ROOT = Path(__file__).resolve().parents[2]

def ok(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    ok((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "14.2.0", "VERSION 14.2.0")
    init_bulk_catalog_schema()
    sample = SimpleNamespace(url="https://example.com/p/sku-1420", product_code="sku-1420", page_number=1, name="Test Telefon 8 GB 256 GB", brand="Test", seller="Mağaza", price=10000.0, old_price=11000.0, stock_status="Stokta", image="https://example.com/a.jpg")
    first = stage_item(store_code="smoke", category_url="https://example.com/c", item=sample)
    second = stage_item(store_code="smoke", category_url="https://example.com/c", item=sample)
    ok(first["action"] in {"inserted", "updated"}, "staging toplu upsert ilk kaydı kabul ediyor")
    ok(second["action"] == "unchanged", "değişmeyen ürün tekrar eşleştirme kuyruğuna alınmıyor")
    sample.price = 9999.0
    third = stage_item(store_code="smoke", category_url="https://example.com/c", item=sample)
    ok(third["action"] == "updated" and third["queued"], "fiyat değişikliği delta olarak kuyruğa alınıyor")
    service = (ROOT / "app/services/bulk_catalog_service.py").read_text(encoding="utf-8")
    ok("from app.services.cross_store_search_service" not in service and "scan_other_stores(" not in service, "toplu alım sırasında çapraz mağaza araması kapalı")
    ok("bulk_catalog_checkpoints" in service, "sayfa checkpoint altyapısı mevcut")
    ok("bulk_match_queue" in service, "toplu eşleştirme kuyruğu mevcut")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    ok("admin_bulk_catalog_router" in main_text, "toplu katalog router uygulamaya bağlı")
    route_text = (ROOT / "app/web/admin_bulk_catalog_routes.py").read_text(encoding="utf-8")
    ok("/api/bulk-catalog/v14/status" in route_text, "toplu katalog durum API mevcut")
    status = catalog_status()
    ok(status["cross_store_search_during_ingestion"] is False, "ingestion ve eşleştirme aşamaları ayrıldı")
    print("\nFırsatAI v14.2.0 Toplu Katalog Motoru smoke test başarılı.")

if __name__ == "__main__":
    raise SystemExit(main())
