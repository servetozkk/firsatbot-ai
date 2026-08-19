from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.5.2", "VERSION 13.5.2")
    from app.services.stock_tracking_service import classify_stock, ENGINE_VERSION
    ok(ENGINE_VERSION == "13.5.2", "stok motoru sürümü doğru")
    low = classify_stock(SimpleNamespace(is_active=True, current_price=100, campaign_text="Son 3 ürün, az kaldı", delivery_text="", shipping_method=""))
    out = classify_stock(SimpleNamespace(is_active=False, current_price=0, campaign_text="", delivery_text="", shipping_method=""))
    instock = classify_stock(SimpleNamespace(is_active=True, current_price=100, campaign_text="Stokta", delivery_text="", shipping_method=""))
    unknown = classify_stock(SimpleNamespace(is_active=True, current_price=0, campaign_text="", delivery_text="", shipping_method=""))
    ok(low["status"] == "low_stock" and low["quantity_hint"] == 3, "az kaldı ve adet ipucu ayrıştırılıyor")
    ok(out["status"] == "out_of_stock", "aktif olmayan teklif tükendi sınıfı alıyor")
    ok(instock["status"] == "in_stock", "stokta metni doğru sınıflandırılıyor")
    ok(unknown["status"] == "unknown", "yetersiz veri bilinmiyor sınıfı alıyor")
    route = (ROOT / "app/web/stock_tracking_routes.py").read_text(encoding="utf-8")
    template = (ROOT / "app/templates/stock_center.html").read_text(encoding="utf-8")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    ok('/stok' in route and '/api/stock-center/v13' in route, "stok merkezi route ve API mevcut")
    ok('stock_tracking_router' in main_text, "stok router uygulamaya bağlı")
    ok('Mağazada doğrula' in template and 'Fiyatları karşılaştır' in template, "stok doğrulama ve karşılaştırma bağlantıları mevcut")
    ok('read_only' in (ROOT / "app/services/stock_tracking_service.py").read_text(encoding="utf-8"), "stok merkezi salt okunur")
    print("\nFırsatAI v13.5.2 Stok Takibi smoke test başarılı.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
