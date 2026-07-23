from __future__ import annotations

import os
import sys

from app.database.database import create_db
from app.services.product_service import save_product
from app.services.scraper_registry import (
    ScraperNotImplementedError,
    ScraperRegistry,
    UnsupportedStoreError,
)


def print_store_statuses(
    registry: ScraperRegistry,
) -> None:
    """
    Registry içerisinde tanımlı mağazaların
    scraper durumlarını terminale yazdırır.
    """

    print()
    print("=" * 80)
    print("MAĞAZA DURUMLARI")
    print("=" * 80)

    for store in registry.list_stores():
        implemented = bool(
            store["implemented"]
        )

        enabled = bool(
            store["enabled"]
        )

        if implemented and enabled:
            status = "AKTİF"

        elif implemented:
            status = "PASİF"

        else:
            status = "SCRAPER BEKLİYOR"

        print(
            f"{store['name']:<24}"
            f"{store['code']:<16}"
            f"{status}"
        )


def print_product(
    product,
) -> None:
    """
    Scraper tarafından döndürülen ürün bilgilerini
    terminale yazdırır.
    """

    print()
    print("=" * 80)
    print("ÜRÜN BİLGİLERİ")
    print("=" * 80)

    print(
        "Ürün adı:",
        product.name,
    )

    print(
        "Fiyat:",
        product.price,
    )

    print(
        "Eski fiyat:",
        product.old_price,
    )

    print(
        "Marka:",
        product.brand,
    )

    print(
        "Model:",
        product.model,
    )

    print(
        "Kategori:",
        product.category,
    )

    print(
        "Satıcı:",
        product.seller,
    )

    print(
        "Puan:",
        product.rating,
    )

    print(
        "Değerlendirme:",
        product.review_count,
    )

    print(
        "Stok:",
        product.stock_status,
    )

    print(
        "Ürün kodu:",
        product.product_code,
    )

    print(
        "Kaynak:",
        product.source_site,
    )

    print(
        "URL:",
        product.url,
    )

    print(
        "Resim:",
        product.image,
    )

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


def get_product_url() -> str:
    """
    Ürün URL'sini ortam değişkenlerinden alır.

    Öncelik:
    1. PRODUCT_URL
    2. HEPSIBURADA_PRODUCT_URL
    3. TRENDYOL_PRODUCT_URL
    """

    variable_names = (
        "PRODUCT_URL",
        "HEPSIBURADA_PRODUCT_URL",
        "TRENDYOL_PRODUCT_URL",
    )

    for variable_name in variable_names:
        value = os.getenv(
            variable_name,
            "",
        ).strip()

        if value:
            return value

    return ""


def main() -> None:
    registry = ScraperRegistry()

    print_store_statuses(
        registry
    )

    product_url = get_product_url()

    if not product_url:
        print()
        print("=" * 80)
        print("ÜRÜN URL'Sİ BULUNAMADI")
        print("=" * 80)

        print(
            "PRODUCT_URL ortam değişkenini tanımla."
        )

        print()
        print("Hepsiburada örneği:")

        print(
            '$env:PRODUCT_URL='
            '"https://www.hepsiburada.com/urun-linki"'
        )

        print()
        print("Trendyol örneği:")

        print(
            '$env:PRODUCT_URL='
            '"https://www.trendyol.com/urun-linki"'
        )

        print()
        print(
            "Ardından:"
        )

        print(
            "python .\\run_scan.py"
        )

        sys.exit(1)

    print()
    print("=" * 80)
    print("TARAMA BAŞLIYOR")
    print("=" * 80)

    print(
        "Girilen URL:",
        product_url,
    )

    print()
    print(
        "Veritabanı hazırlanıyor..."
    )

    create_db()

    try:
        store_definition = registry.detect_store(
            product_url
        )

        print(
            "Tespit edilen mağaza:",
            store_definition.name,
        )

        print(
            "Mağaza kodu:",
            store_definition.code,
        )

        product = registry.scrape(
            product_url
        )

        if product is None:
            raise RuntimeError(
                "Scraper ürün bilgisi döndürmedi."
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
        print("=" * 80)
        print("İŞLEM BAŞARILI")
        print("=" * 80)

        print(
            "Ürün başarıyla tarandı ve "
            "veritabanına kaydedildi."
        )

    except ScraperNotImplementedError as error:
        print()
        print("=" * 80)
        print("SCRAPER HENÜZ HAZIR DEĞİL")
        print("=" * 80)

        print(
            error
        )

        sys.exit(2)

    except UnsupportedStoreError as error:
        print()
        print("=" * 80)
        print("DESTEKLENMEYEN MAĞAZA")
        print("=" * 80)

        print(
            error
        )

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