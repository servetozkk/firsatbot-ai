from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.product import Product
from app.services.offer_matching_service import OfferMatchingService
from app.services.product_identity_service import ProductIdentityService


def product(name: str) -> Product:
    return Product(name=name, price=1, old_price=None, rating=None, review_count=None,
                   seller="", url="https://test.local/" + str(abs(hash(name))), image=None)


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    same_left = ProductIdentityService.parse(product("Lenovo V15 16GB RAM 512SSD"))
    same_right = ProductIdentityService.parse(product("Lenovo V15 16GB RAM 512 GB SSD"))
    score, _ = OfferMatchingService.score(same_left, same_right)
    ok(score >= OfferMatchingService.MIN_MATCH_SCORE, "aynı varyant yüksek skor alıyor")

    storage_left = ProductIdentityService.parse(product("Samsung Galaxy A17 5G 8GB 256GB"))
    storage_right = ProductIdentityService.parse(product("Samsung Galaxy A17 5G 8GB 512GB"))
    score, reasons = OfferMatchingService.score(storage_left, storage_right)
    ok(score == 0 and any("depolama" in r for r in reasons), "farklı storage taşıma adayı olmuyor")

    network_right = ProductIdentityService.parse(product("Samsung Galaxy A17 4G 8GB 256GB"))
    score, reasons = OfferMatchingService.score(storage_left, network_right)
    ok(score == 0 and any("şebeke" in r for r in reasons), "4G ve 5G birleştirme adayı olmuyor")

    ram_right = ProductIdentityService.parse(product("Lenovo V15 32GB RAM 512GB SSD"))
    score, reasons = OfferMatchingService.score(same_left, ram_right)
    ok(score == 0 and any("RAM" in r for r in reasons), "farklı RAM taşıma adayı olmuyor")

    ok((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "11.2.1", "VERSION 11.2.1")
    print("\nFırsatAI v11.2.1 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
