from types import SimpleNamespace

from app.models.product import Product
from app.services.offer_matching_service import OfferMatchingService
from app.services.product_identity_service import ProductIdentityService


def product(name: str, *, brand: str, category: str = "telefon") -> Product:
    return Product(
        name=name,
        price=1,
        old_price=None,
        rating=None,
        review_count=None,
        seller="",
        url="https://example.com/" + name.replace(" ", "-"),
        image=None,
        brand=brand,
        model=None,
        category=category,
    )


def group(group_id: int, item: Product):
    return SimpleNamespace(
        id=group_id,
        identity_source=ProductIdentityService.build_identity_source(item),
        canonical_name=item.name,
        brand=ProductIdentityService.normalize_token(item.brand),
        model=ProductIdentityService.get_normalized_model(item),
        category=item.category,
    )


def test_same_phone_different_writing_matches():
    incoming = product("Apple iPhone 16 Pro 256GB Black", brand="Apple")
    candidate_product = product("iPhone 16 Pro Siyah 256 GB", brand="Apple")
    candidate = group(1, candidate_product)
    ranked = OfferMatchingService.rank_groups(incoming, [candidate])
    assert ranked and ranked[0][1] >= OfferMatchingService.MIN_MATCH_SCORE


def test_storage_conflict_is_rejected():
    incoming = ProductIdentityService.parse(product("Apple iPhone 16 Pro 256GB", brand="Apple"))
    candidate = ProductIdentityService.parse(product("Apple iPhone 16 Pro 512GB", brand="Apple"))
    score, reasons = OfferMatchingService.score(incoming, candidate, incoming_category="telefon", candidate_category="telefon")
    assert score == 0
    assert any("depolama" in reason for reason in reasons)


def test_variant_conflict_is_rejected():
    incoming = ProductIdentityService.parse(product("Samsung Galaxy S25 256GB", brand="Samsung"))
    candidate = ProductIdentityService.parse(product("Samsung Galaxy S25 FE 256GB", brand="Samsung"))
    score, reasons = OfferMatchingService.score(incoming, candidate, incoming_category="telefon", candidate_category="telefon")
    assert score == 0
    assert any("varyant" in reason for reason in reasons)


def test_category_conflict_is_rejected():
    incoming = ProductIdentityService.parse(product("Xiaomi 17 256GB", brand="Xiaomi", category="telefon"))
    candidate = ProductIdentityService.parse(product("Xiaomi 17 256GB", brand="Xiaomi", category="tablet"))
    score, reasons = OfferMatchingService.score(incoming, candidate, incoming_category="telefon", candidate_category="tablet")
    assert score == 0
    assert any("kategori" in reason for reason in reasons)
