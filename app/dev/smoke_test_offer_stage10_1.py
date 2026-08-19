from pathlib import Path

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    root = Path(__file__).resolve().parents[2]
    template = (root / "app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    checks = {
        "yeni ürün güven şeridi": "product-trust-strip",
        "profesyonel fiyat kutusu": "hero-price-main",
        "teklif bulunamadı boş durumu": "hero-empty-offer",
        "ürün içgörü şeridi": "product-insight-strip",
        "mobil sabit teklif butonu": "mobile-detail-cta",
        "aktif teklif koşulu": "{% if available_offers and comparison.best_price is not none %}",
    }
    for label, marker in checks.items():
        check(marker in template, label)
    print("\nTeklif Sistemi Aşama 10.1 smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
