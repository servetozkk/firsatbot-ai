from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService


def p(name, brand, category):
    return Product(name=name, price=1, old_price=None, rating=0, review_count=0,
                   seller="", url="x", image="", brand=brand, category=category,
                   description="", specifications={}, source_site="test", product_code="")


def test_v239_tablet_family_clean():
    x = ProductIdentityService.explain(p("Samsung Galaxy Tab A11 8GB 128GB Gümüş Tablet", "Samsung", "Tablet"))
    assert x["family"] == "galaxy tab a11"
    assert x["storage_gb"] == 128
    assert "gumus" not in x["family"] and "tablet" not in x["family"]


def test_v239_audio_family_clean():
    x = ProductIdentityService.explain(p("Xiaomi Redmi Buds 6 Play Siyah", "Xiaomi", "Kulaklık"))
    assert x["family"] == "redmi buds 6 play"
    assert "siyah" not in x["identity_source"]


def test_v239_iphone_family_preserved():
    x = ProductIdentityService.explain(p("Apple iPhone 16 128 GB", "Apple", "Cep Telefonu"))
    assert x["family"] == "iphone 16"
    assert x["storage_gb"] == 128


def test_v239_wearable_variant_preserved():
    x = ProductIdentityService.explain(p("Apple Watch SE 3 GPS 44mm", "Apple", "Akıllı Saat"))
    assert x["family"] == "apple watch se"
    assert x["variant"] == "3"
