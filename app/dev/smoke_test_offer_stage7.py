from pathlib import Path

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    root = Path(__file__).resolve().parents[2]
    template = (root / "app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    checks = {
        "profesyonel teklif başlığı": "offer-market-head",
        "mağaza filtreleri": "data-offer-store",
        "filtre temizleme": "offerClearFilters",
        "masaüstü Satıcıya Git": "Satıcıya Git",
        "mobil teklif kartları": "offer-mobile-card",
        "önerilen sıralama": 'value="recommended"',
    }
    for label, marker in checks.items():
        check(marker in template, label)
    print("\nTeklif Sistemi Aşama 7 smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
