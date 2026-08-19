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

    samples = [
        ("Samsung Türkiye garantili", "Türkiye garantili"),
        ("2 Yıl Garanti", "2 yıl garanti"),
        ("İthalatçı Garantili", "İthalatçı garantili"),
        ("Distribütör Garantili", "Distribütör garantili"),
    ]

    for text, expected_fragment in samples:
        product = Product(
            name="Test Ürün",
            price=1000,
            old_price=None,
            rating=None,
            review_count=0,
            seller="Test",
            url="https://example.com",
            image=None,
            description=text,
            stock_status="Stokta",
            source_site="Test",
        )
        details = normalize_offer_details(product)
        check(
            bool(details.warranty_type)
            and expected_fragment.casefold() in details.warranty_type.casefold(),
            f"garanti algılandı: {text}",
        )

    print("\nAşama 5 garanti ayrıştırma testi başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
