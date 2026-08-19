from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.product import Product
from app.services.category_aware_matcher_v221 import match_products_category_aware_v221



def p(*, name: str, brand: str, model: str, category: str, price: float = 1000.0, site: str = "test", product_code: str = "") -> Product:
    return Product(
        name=name,
        price=price,
        old_price=None,
        rating=None,
        review_count=None,
        seller="test",
        url="https://example.test/product",
        image=None,
        brand=brand,
        model=model,
        category=category,
        source_site=site,
        product_code=product_code,
    )


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def assert_match(source: Product, candidate: Product, label: str) -> None:
    matched, score, reason = match_products_category_aware_v221(
        source_product=source,
        candidate_product=candidate,
        minimum_score=0.82,
    )
    check(matched, f"{label}: GREEN {score:.3f} / {reason}")


def assert_red(source: Product, candidate: Product, label: str) -> None:
    matched, score, reason = match_products_category_aware_v221(
        source_product=source,
        candidate_product=candidate,
        minimum_score=0.82,
    )
    check(not matched, f"{label}: RED / {reason}")


def main() -> None:
    check((ROOT / "VERSION").read_text(encoding="utf-8-sig").strip() == "23.11.0", "VERSION 23.11.0")

    lenovo = p(
        name="LENOVO Ideapad Slim 3 Intel N100 4GB RAM 128GB SSD 15.6 82XB009GTX",
        brand="lenovo",
        model="ideapad slim 3 intel n100 4gb ram 128gb ssd 15.6 82xb009gtx",
        category="Elektronik > Bilgisayar > Laptop",
    )
    assert_match(
        lenovo,
        p(name="Lenovo IdeaPad Slim 3 Intel N100 4GB 128GB SSD W11 Notebook 82XB009GTX", brand="Lenovo", model="IdeaPad Slim 3 N100 4GB 128GB 82XB009GTX", category="Laptop", site="teknosa"),
        "Lenovo exact MTM detail-stage",
    )
    assert_red(
        lenovo,
        p(name="Lenovo IdeaPad Slim 3 Intel N100 4GB 128GB SSD W11 Notebook 82XB009HTX", brand="Lenovo", model="IdeaPad Slim 3 N100 4GB 128GB 82XB009HTX", category="Laptop", site="hepsiburada"),
        "Lenovo wrong MTM",
    )

    mac = p(
        name='Apple 13" MacBook Neo Indigo 256GB',
        brand="apple",
        model="13 macbook neo indigo 256gb",
        category="Elektronik > Bilgisayar > Laptop",
    )
    assert_match(
        mac,
        p(name="Apple MacBook Neo A18 Pro 8GB 256GB SSD 13 inch Indigo", brand="Apple", model="MacBook Neo A18 Pro 8GB 256GB SSD", category="Laptop", site="teknosa"),
        "MacBook Neo 256 detail-stage",
    )
    assert_red(
        mac,
        p(name="Apple MacBook Neo A18 Pro 8GB 512GB SSD 13 inch Indigo", brand="Apple", model="MacBook Neo A18 Pro 8GB 512GB SSD", category="Laptop"),
        "MacBook wrong storage",
    )

    buds = p(
        name="Xiaomi Redmi Buds 6 Play Pembe Kulakici Kulaklik",
        brand="xiaomi",
        model="Redmi Buds 6 Play Pembe Kulakici Kulaklik",
        category="Elektronik > Kulaklik > Bluetooth Kulaklik",
    )
    assert_match(
        buds,
        p(name="Xiaomi Redmi Buds 6 Play Bluetooth Kulaklik Siyah", brand="Xiaomi", model="Redmi Buds 6 Play Bluetooth Kulaklik", category="Bluetooth Kulaklik", site="teknosa"),
        "Redmi Buds family detail-stage",
    )
    assert_red(
        buds,
        p(name="Xiaomi Redmi Buds 6 Play Kilif Silikon Koruma Kabi", brand="Xiaomi", model="Redmi Buds 6 Play Kilif", category="Kulaklik Aksesuari"),
        "Redmi Buds accessory guard",
    )

    tablet = p(
        name="Samsung Galaxy Tab A11 8GB 128GB Gumus Tablet",
        brand="samsung",
        model="Galaxy Tab A11 8GB 128GB Gumus Tablet",
        category="Elektronik > Bilgisayar&Tablet > Tablet > Samsung Tablet",
    )
    assert_match(
        tablet,
        p(name='Samsung Galaxy Tab A11 SM-X130 8 GB 128 GB 8.7 Tablet Gumus', brand="Samsung", model="Galaxy Tab A11 8 GB 128 GB", category="Tablet"),
        "Galaxy Tab A11 detail-stage",
    )
    assert_red(
        tablet,
        p(name="Samsung Galaxy Tab A11 8GB 256GB Tablet", brand="Samsung", model="Galaxy Tab A11 8GB 256GB Tablet", category="Tablet"),
        "Galaxy Tab wrong storage",
    )

    watch = p(
        name="Apple Watch SE 3 GPS 44mm",
        brand="apple",
        model="Watch SE 3 GPS 44mm",
        category="Giyilebilir Teknoloji > Akilli Saat",
    )
    assert_match(
        watch,
        p(name="Apple Watch SE 3 GPS 44mm", brand="Apple", model="Watch SE 3 GPS 44mm", category="Akilli Saat"),
        "Wearable v22.5 preserved",
    )
    assert_red(
        watch,
        p(name="Apple Watch SE 2 GPS 44mm", brand="Apple", model="Watch SE 2 GPS 44mm", category="Akilli Saat"),
        "Wearable wrong variant preserved",
    )

    phone = p(
        name="Xiaomi Redmi Note 15 Pro 256GB 5G",
        brand="xiaomi",
        model="Redmi Note 15 Pro 256GB 5G",
        category="Cep Telefonu",
    )
    assert_match(
        phone,
        p(name="Xiaomi Redmi Note 15 Pro 256GB 5G", brand="Xiaomi", model="Redmi Note 15 Pro 256GB 5G", category="Akilli Telefon"),
        "Phone variant/network preserved",
    )
    assert_red(
        phone,
        p(name="Xiaomi Redmi Note 15 Pro 256GB", brand="Xiaomi", model="Redmi Note 15 Pro 256GB", category="Akilli Telefon"),
        "Phone base/5G guard preserved",
    )

    original = p(
        name="Apple 20W USB-C Guc Adaptoru MD3J4TU/A",
        brand="apple",
        model="MD3J4TU/A",
        category="Sarj Aleti",
    )
    compatible = p(
        name="Apple Uyumlu 20W USB-C Guc Adaptoru MD3J4TU/A",
        brand="apple",
        model="MD3J4TU/A",
        category="Sarj Aleti",
    )
    assert_red(original, compatible, "v23.6 original-vs-compatible guard preserved")

    print("OK  FirsatAI v23.11 smoke test tamamlandi")


if __name__ == "__main__":
    main()
