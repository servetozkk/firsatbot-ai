from app.models.product import Product
from app.services.strict_product_matcher_v17 import match_products_v17


def product(name: str, model: str | None = None, brand: str = "Asus", price: float = 25000) -> Product:
    return Product(
        name=name, price=price, old_price=None, rating=0, review_count=0,
        seller="Test", url="https://example.com/p", image=None,
        brand=brand, model=model,
    )


def expect(label: str, expected: bool, candidate: Product) -> None:
    source = product(
        "ASUS Vivobook 15 X1504VA-BQ5391 Intel Core 5 120U 8GB RAM 512GB SSD 15.6 FHD",
        "X1504VA-BQ5391",
    )
    matched, score, reason = match_products_v17(
        source_product=source,
        candidate_product=candidate,
    )
    assert matched is expected, (label, matched, score, reason)
    print("OK ", label, score, reason)


def main() -> int:
    expect(
        "tam BQ5391 kabul",
        True,
        product("ASUS Vivobook 15 X1504VA-BQ5391 Core 5 120U 8GB RAM 512GB SSD 15.6"),
    )
    expect(
        "son eki eksik ama teknik özellikleri aynı aday kabul",
        True,
        product("ASUS Vivobook 15 X1504VA Core 5 120U 8GB RAM 512GB SSD 15.6", "X1504VA"),
    )
    expect(
        "BQ5383W kesin red",
        False,
        product("ASUS Vivobook 15 X1504VA-BQ5383W Core 5 120U 8GB RAM 512GB SSD 15.6"),
    )
    expect(
        "BQ5387 kesin red",
        False,
        product("ASUS Vivobook 15 X1504VA-BQ5387 Core 5 120U 8GB RAM 512GB SSD 15.6"),
    )
    expect(
        "NJ3663W kesin red",
        False,
        product("ASUS Vivobook 15 X1504VA-NJ3663W Core 5 120U 8GB RAM 512GB SSD 15.6"),
    )
    expect(
        "TUF farklı seri ve model kesin red",
        False,
        product("ASUS TUF Gaming A16 FA608UM-RV131 Ryzen 7 16GB RAM 512GB SSD 16"),
    )
    expect(
        "Samsung kesin red",
        False,
        product("Samsung Galaxy Z Fold6 512GB 12GB RAM", brand="Samsung"),
    )
    expect(
        "farklı depolama kesin red",
        False,
        product("ASUS Vivobook 15 X1504VA Core 5 120U 8GB RAM 1TB SSD 15.6", "X1504VA"),
    )
    expect(
        "güvenlik sayfası kesin red",
        False,
        product("Attention Required! Cloudflare security verification", model="X1504VA-BQ5391"),
    )
    print("FirsatAI v17 strict matcher smoke test successful")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
