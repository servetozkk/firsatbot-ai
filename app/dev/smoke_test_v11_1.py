from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.product import Product
from app.services.cross_store_search_service import CrossStoreSearchService
from app.services.offer_integrity_service import validate_variant
from app.services.product_identity_service import ProductIdentityService


def make(name: str) -> Product:
    return Product(
        name=name,
        price=100,
        old_price=None,
        rating=None,
        review_count=None,
        seller="Test",
        url="https://test.invalid/" + name.replace(" ", "-"),
        image=None,
        brand="Xiaomi",
        model=None,
        category="Cep Telefonu",
    )


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    source = make("Xiaomi 17 12G+256G Siyah")
    same = make("Xiaomi 17 5G 12G+256GB Mavi")
    wrong = make("Xiaomi 17 5G 12G+512GB Yeşil")

    source_id = ProductIdentityService.parse(source)
    same_id = ProductIdentityService.parse(same)
    wrong_id = ProductIdentityService.parse(wrong)

    check(
        source_id.ram_gb == 12 and source_id.storage_gb == 256,
        "12G+256G RAM ve depolama doğru ayrıştırılıyor",
    )
    check(
        wrong_id.ram_gb == 12 and wrong_id.storage_gb == 512,
        "12G+512GB RAM ve depolama doğru ayrıştırılıyor",
    )
    check(
        validate_variant(source_id, same_id).compatible,
        "aynı teknik varyant kabul ediliyor",
    )
    check(
        not validate_variant(source_id, wrong_id).compatible,
        "256 GB ile 512 GB zorunlu kapıda reddediliyor",
    )

    matched_same, _, _ = CrossStoreSearchService._is_same_product(source, same)
    matched_wrong, _, reason_wrong = CrossStoreSearchService._is_same_product(
        source,
        wrong,
    )
    check(matched_same, "aynı kapasite mağaza adayı eşleşiyor")
    check(
        not matched_wrong and "varyant" in reason_wrong.casefold(),
        "farklı kapasite cross-store eşleşmesinde reddediliyor",
    )

    identity_source = ProductIdentityService.build_identity_source(source)
    check(
        "ram=12gb" in identity_source and "storage=256gb" in identity_source,
        "kimlik kaynağı RAM ve depolamayı ayrı saklıyor",
    )

    print("\nFırsatAI v11.1 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
