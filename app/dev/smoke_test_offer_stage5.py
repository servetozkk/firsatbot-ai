from __future__ import annotations

import sys
from pathlib import Path

def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main() -> int:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.models.product import Product
    from app.services.offer_detail_service import normalize_offer_details

    product = Product(
        name="Samsung Galaxy S25 Ultra 512 GB - Ücretsiz Kargo",
        price=80000,
        old_price=85000,
        rating=4.8,
        review_count=250,
        seller="Teknosa",
        url="https://www.teknosa.com/test",
        image=None,
        description="Samsung Türkiye garantili. Yarın kargoda. Peşin fiyatına 3 taksit.",
        stock_status="Stokta",
        source_site="Teknosa",
    )
    details = normalize_offer_details(product)
    check(details.shipping_price == 0.0, "ücretsiz kargo algılanıyor")
    check(details.is_official_seller, "mağaza kendi satıcısı resmî kabul ediliyor")
    check(bool(details.delivery_text), "teslimat metni algılanıyor")
    check(bool(details.warranty_type), "garanti türü algılanıyor")
    check(bool(details.installment_text), "taksit bilgisi algılanıyor")
    check(hasattr(product, "campaign_text"), "Product teklif alanlarını taşıyor")

    source = (root / "app/services/multi_store_service.py").read_text(encoding="utf-8")
    check("apply_offer_details" in source, "teklif kayıt hattı ayrıntı servisine bağlı")

    print("\\nTeklif Sistemi Aşama 5 smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
