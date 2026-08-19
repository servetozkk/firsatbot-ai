from pathlib import Path

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    root = Path(__file__).resolve().parents[2]
    template = (root / "app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    checks = {
        "stok filtresi": 'data-offer-filter="in-stock"',
        "garanti filtresi": 'data-offer-filter="warranty"',
        "taksit filtresi": 'data-offer-filter="installment"',
        "kampanya filtresi": 'data-offer-filter="campaign"',
        "teslimat sıralaması": 'value="delivery"',
        "kart teslimat verisi": 'data-delivery=',
        "aktif filtre özeti": 'offerActiveFilterSummary',
        "filtre boş durumu": 'Uygun teklif bulunamadı',
    }
    for label, marker in checks.items():
        check(marker in template, label)
    print("\nTeklif Sistemi Aşama 10.3 smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
