from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService


def sample(name: str, brand=None):
    p = Product(name=name, price=1, old_price=None, rating=None, review_count=None,
                seller="test", url="https://example.com/x", image=None, brand=brand)
    ProductIdentityService.enrich_product(p)
    return p


def main():
    cases = [
        ("iPhone 15 256 Gb Akıllı Telefon Mavi", "Apple", "iPhone 15"),
        ("Samsung Galaxy A07 4 GB 128 GB Siyah", "Samsung", "Galaxy A07"),
        ("Xiaomi Redmi 15C 8 + 256 GB Yeşil", "Xiaomi", "Redmi 15C"),
        ("Samsung Galaxy S25 Ultra 512 GB 12 GB Ram Mavi", "Samsung", "Galaxy S25 Ultra"),
        ("Samsung Fold8 Ultra 5G 1TB Mürdüm", "Samsung", "Fold8 Ultra"),
    ]
    for name, brand, model in cases:
        p = sample(name)
        assert p.brand == brand, (name, p.brand)
        assert p.model.casefold() == model.casefold(), (name, p.model)
        print("OK", p.brand, p.model, ProductIdentityService.build_identity_source(p))


if __name__ == "__main__":
    main()
