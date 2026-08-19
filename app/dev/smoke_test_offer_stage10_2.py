from pathlib import Path

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    root = Path(__file__).resolve().parents[2]
    template = (root / "app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    checks = {
        "masaüstü gerçek teklif listesi": "offer-desktop-list",
        "mağaza kartı": "offer-market-card",
        "mağaza ve satıcı alanı": "offer-card-store",
        "kargo teslimat garanti alanı": "offer-card-services",
        "kargo dahil fiyat": "offer-card-price",
        "satıcıya git aksiyonu": "offer-card-go",
        "mobil kartların korunması": "offer-mobile-list",
        "filtre JS yeni listeyi kullanıyor": "#offerDesktopList [data-offer-item]",
    }
    for label, marker in checks.items():
        check(marker in template, label)
    print("\nTeklif Sistemi Aşama 10.2 smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
