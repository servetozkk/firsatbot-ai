from app.models.product import Product
from app.services.multi_store_service import build_group_identity


def make_product(
    *,
    name: str,
    url: str,
    source_site: str,
    model: str,
) -> Product:
    return Product(
        name=name,
        price=5999.0,
        old_price=None,
        rating=4.8,
        review_count=100,
        seller=source_site,
        url=url,
        image=None,
        brand="AOC",
        model=model,
        category="Monitör",
        description=None,
        specifications=None,
        stock_status="Stokta",
        source_site=source_site,
        product_code=None,
    )


hepsiburada = make_product(
    name='Aoc 27" 27G4HA Fast IPS 1ms 200Hz',
    url="https://www.hepsiburada.com/test",
    source_site="hepsiburada",
    model="27 27G4HA Fast IPS 1m 200HZ HDMI DP",
)

trendyol = make_product(
    name="AOC 27G4HA 27 inç 200 Hz Oyuncu Monitörü",
    url="https://www.trendyol.com/test",
    source_site="trendyol",
    model="27G4HA",
)

hb_identity = build_group_identity(
    hepsiburada
)

ty_identity = build_group_identity(
    trendyol
)

print("Hepsiburada:", hb_identity)
print("Trendyol    :", ty_identity)
print()
print(
    "Aynı ürün grubu:",
    hb_identity[0] == ty_identity[0],
)

assert hb_identity[0] == ty_identity[0]
assert hb_identity[1] == "brand_model:aoc|27g4ha"
assert ty_identity[1] == "brand_model:aoc|27g4ha"

print("Sprint 2 kimlik testi başarılı.")
