from __future__ import annotations

import os
import sys

from app.database.database import create_db
from app.scrapers.hepsiburada import (
    HepsiburadaScraper,
)
from app.services.product_service import (
    save_product,
)


def print_product(product) -> None:
    print()
    print("=" * 70)
    print("HEPSİBURADA ÜRÜN BİLGİLERİ")
    print("=" * 70)
    print("Ürün adı:", product.name)
    print("Fiyat:", product.price)
    print("Eski fiyat:", product.old_price)
    print("Marka:", product.brand)
    print("Model:", product.model)
    print("Kategori:", product.category)
    print("Satıcı:", product.seller)
    print("Puan:", product.rating)
    print("Değerlendirme:", product.review_count)
    print("Stok:", product.stock_status)
    print("Ürün kodu:", product.product_code)
    print("Kaynak:", product.source_site)
    print("Resim:", product.image)

    specification_count = 0

    if isinstance(
        product.specifications,
        dict,
    ):
        specification_count = len(
            product.specifications
        )

    print(
        "Teknik özellik sayısı:",
        specification_count,
    )


def main() -> None:
    product_url = os.getenv(
        "HEPSIBURADA_PRODUCT_URL",
        "",
    ).strip()

    if not product_url:
        print(
            "HEPSIBURADA_PRODUCT_URL tanımlanmadı."
        )

        print()
        print(
            "Örnek kullanım:"
        )

        print(
            '$env:HEPSIBURADA_PRODUCT_URL='
            '"https://www.hepsiburada.com/...-p-HBCV..."'
        )

        print(
            "python .\\run_hepsiburada_scan.py"
        )

        sys.exit(1)

    print(
        "Veritabanı hazırlanıyor..."
    )

    create_db()

    scraper = HepsiburadaScraper()

    try:
        product = scraper.scrape(
            product_url
        )

        print_product(product)

        print()
        print("=" * 70)
        print("VERİTABANINA KAYIT BAŞLIYOR")
        print("=" * 70)

        save_product(product)

        print()
        print(
            "Hepsiburada ürünü başarıyla kaydedildi."
        )

    except Exception as error:
        print()
        print("=" * 70)
        print("İŞLEM BAŞARISIZ")
        print("=" * 70)

        print(
            "Hata türü:",
            type(error).__name__,
        )

        print(
            "Hata:",
            error,
        )

        raise


if __name__ == "__main__":
    main()