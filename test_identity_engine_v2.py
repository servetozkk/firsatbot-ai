from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService


def product(name: str, brand: str = "Samsung") -> Product:
    return Product(
        name=name,
        price=1000.0,
        old_price=None,
        rating=None,
        review_count=None,
        seller="Test",
        url="https://example.com/" + str(abs(hash(name))),
        image=None,
        brand=brand,
        source_site="test",
    )


def main() -> None:
    cases = [
        product("Samsung Fold8 Ultra 5G 1TB Mürdüm Akıllı Telefon Fiyatı ve Özellikleri"),
        product("Samsung Fold8 Ultra 5G 256 GB Mürdüm Akıllı Telefon Fiyatı ve Özellikleri"),
        product("Samsung Fold8 Ultra 5G 1TB Gri Akıllı Telefon Fiyatı ve Özellikleri"),
        product("Samsung Fold8 5G 512 GB Gri Akıllı Telefon Fiyatı ve Özellikleri"),
        product("Apple iPhone 17 Pro Max 12 GB 512 GB Siyah", "Apple"),
        product("Apple iPhone 17 Pro Max 12 GB 1 TB Beyaz", "Apple"),
    ]

    explanations = [ProductIdentityService.explain(item) for item in cases]
    for item, explanation in zip(cases, explanations):
        print("\n", item.name)
        print(explanation)

    assert explanations[0]["identity_key"] != explanations[1]["identity_key"]
    assert explanations[0]["identity_key"] == explanations[2]["identity_key"]
    assert explanations[0]["identity_key"] != explanations[3]["identity_key"]
    assert explanations[4]["identity_key"] != explanations[5]["identity_key"]
    assert explanations[0]["storage_gb"] == 1024
    assert explanations[1]["storage_gb"] == 256
    assert explanations[0]["variant"] == "ultra"
    print("\nIDENTITY ENGINE V2 TESTLERİ BAŞARILI")


if __name__ == "__main__":
    main()
