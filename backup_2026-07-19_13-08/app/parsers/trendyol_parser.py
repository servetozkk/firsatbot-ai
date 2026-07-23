import json
from selectolax.parser import HTMLParser

from app.models.product import Product


class TrendyolParser:

    def parse(self, html: str, url: str):

        parser = HTMLParser(html)

        scripts = parser.css(
            'script[type="application/ld+json"]'
        )

        for script in scripts:

            try:
                data = json.loads(script.text())

                # Eğer bu JSON ürün bilgisi değilse geç
                if "name" not in data:
                    continue

                offers = data.get("offers", {})
                rating = data.get("aggregateRating", {})

                product = Product(
                    name=data.get("name", "Bilinmeyen ürün"),

                    price=float(
                        offers.get("price", 0)
                    ),

                    old_price=None,

                    rating=float(
                        rating.get("ratingValue", 0)
                    ),

                    review_count=int(
                        rating.get("reviewCount", 0)
                    ),

                    seller="Trendyol",

                    url=url,

                    image=(data.get("image", {})
    .get("contentUrl", [None])[0]
    if isinstance(data.get("image"), dict)
    else data.get("image")
)
                )

                return product

            except Exception as e:
                print("JSON okuma hatası:", e)

        return None