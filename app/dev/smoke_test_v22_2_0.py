from pathlib import Path

from app.services.semantic_price_v222 import choose_semantic_sale_price
from app.parsers.teknosa_parser import TeknosaParser

text = (
    "Apple iPhone 17 Pro Max Alışveriş kredisi ile ayda 44.956,14 TL "
    "121.999 TL Sepete Ekle 121.999 TL"
)
price, debug = choose_semantic_sale_price(
    text, selected_price=44956.14, min_price=500, max_price=500000
)
assert price == 121999.0, (price, debug)
assert debug["reason"] == "INSTALLMENT_OR_CREDIT_VALUE_REPLACED"

html = '''<html><head><meta property="og:title" content="Apple iPhone 17 Pro Max 256GB Abis Akıllı Telefon"></head><body>
<h1>Apple iPhone 17 Pro Max 256GB Abis Akıllı Telefon</h1>
<div class="product-price">Alışveriş kredisi ile ayda 44.956,14 TL 121.999 TL Sepete Ekle 121.999 TL</div>
<div>Marka: Apple</div></body></html>'''
product = TeknosaParser().parse(
    html,
    "https://www.teknosa.com/apple-iphone-17-pro-max-256gb-abis-akilli-telefon-p-100000058778",
)
assert product.price == 121999.0, product.price

generic = (Path(__file__).resolve().parents[1] / "scrapers" / "generic_store.py").read_text(encoding="utf-8")
assert "_strong_product_evidence" in generic
assert "_blocking_security_page" in generic
assert "security_detector=self._blocking_security_page" in generic
assert "V22.2 challenge classifier" in generic

print("OK V22.2 semantic price + challenge classifier smoke")
