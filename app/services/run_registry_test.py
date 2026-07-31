from __future__ import annotations

import os
import sys

from app.database.database import (
    create_db,
)
from app.services.product_service import (
    save_product,
)
from app.services.scraper_registry import (
    ScraperNotImplementedError,
    ScraperRegistry,
    UnsupportedStoreError,
)


def print_supported_stores(
    registry: ScraperRegistry,
) -> None:
    print()
    print("=" * 80)
    print("MAĞAZA SCRAPER DURUMLARI")
    print("=" * 80)

    for store in registry.list_stores():
        if store["implemented"]:
            status = "AKTİF"
        else:
            status = "BEKLİYOR"

        print(
            f"{store['name']:<22} "
            f"{store['code']:<15} "
            f"{status}"
        )


def print_product(
    product,
) -> None:
    print()
    print("=" * 80)
    print("ÜRÜN BİLGİLERİ")
    print("=" * 80)
    print("Ürün adı:", product.name)
    print("Fiyat:", product.price)
    print("Eski fiyat:", product.old_price)
    print("Marka:", product.brand)
    print("Model:", product.model)
    print("Kategori:", product.category)
    print("Satıcı:", product.seller)
    print("Puan:", product.rating)
    print(
        "Değerlendirme:",
        product.review_count,
    )
    print("Stok:", product.stock_status)
    print("Ürün kodu:", product.product_code)
    print("Kaynak:", product.source_site)
    print("URL:", product.url)


def main() -> None:
    registry = ScraperRegistry()

    print_supported_stores(
        registry
    )

    product_url = os.getenv(
        "PRODUCT_URL",
        "",
    ).strip()

    if not product_url:
        product_url = os.getenv(
            "HEPSIBURADA_PRODUCT_URL",
            "",
        ).strip()

    if not product_url:
        print()
        print(
            "PRODUCT_URL ortam değişkeni "
            "tanımlanmadı."
        )

        print()
        print("Örnek:")
        print(
            '$env:PRODUCT_URL='
            '"https://www.hepsiburada.com/..."'
        )
        print(
            "python .\\run_registry_test.py"
        )

        sys.exit(1)

    print()
    print(
        "Veritabanı hazırlanıyor..."
    )

    create_db()

    try:
        product = registry.scrape(
            product_url
        )

        print_product(
            product
        )

        print()
        print("=" * 80)
        print("VERİTABANINA KAYIT")
        print("=" * 80)

        save_product(
            product
        )

        print()
        print(
            "Registry testi başarıyla tamamlandı."
        )

    except ScraperNotImplementedError as error:
        print()
        print("=" * 80)
        print("SCRAPER HENÜZ HAZIR DEĞİL")
        print("=" * 80)
        print(error)
        sys.exit(2)

    except UnsupportedStoreError as error:
        print()
        print("=" * 80)
        print("DESTEKLENMEYEN MAĞAZA")
        print("=" * 80)
        print(error)
        sys.exit(3)

    except KeyboardInterrupt:
        print()
        print(
            "İşlem kullanıcı tarafından durduruldu."
        )
        sys.exit(130)

    except Exception as error:
        print()
        print("=" * 80)
        print("İŞLEM BAŞARISIZ")
        print("=" * 80)
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
