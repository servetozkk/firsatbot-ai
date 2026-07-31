from app.utils.price_normalizer import PriceNormalizer
from app.category_scrapers.hepsiburada import HepsiburadaCategoryScraper

CASES = {
    "48.499 TL": 48499.0,
    "48.499,00 TL": 48499.0,
    "₺49.999,90": 49999.90,
    "49 999 TL": 49999.0,
    "48,499.90 TRY": 48499.90,
}
for raw, expected in CASES.items():
    actual = PriceNormalizer.normalize(raw)
    assert actual is not None and abs(actual - expected) < 0.01, (raw, actual, expected)

current, old = PriceNormalizer.select_offer_prices([
    "48.499,00 TL",
    "52.999,00 TL",
])
assert current == 48499.0
assert old == 52999.0

# Product-title numbers (iPhone 15, 128 GB, 5G) must never become a price.
html_payload = [{
    "url": "https://www.hepsiburada.com/apple-iphone-15-128-gb-5g-p-HBCV000TEST",
    "name": "Apple iPhone 15 128 GB 5G",
    "price_candidates": ["48.499,00 TL", "52.999,00 TL"],
    "card_text": "Apple iPhone 15 128 GB 5G 48.499,00 TL",
}]
cards = HepsiburadaCategoryScraper.extract_product_cards_from_payload(
    html_payload,
    category_url="https://www.hepsiburada.com/cep-telefonlari-c-371965",
    page_number=1,
)
assert len(cards) == 1
assert cards[0].price == 48499.0
assert cards[0].old_price == 52999.0
print("PRICE NORMALIZER V1 TESTLERİ BAŞARILI")
print("GÜNCEL FİYAT:", cards[0].price)
print("ESKİ FİYAT:", cards[0].old_price)
