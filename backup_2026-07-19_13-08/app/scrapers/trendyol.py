import requests
from selectolax.parser import HTMLParser

from app.parsers.trendyol_parser import TrendyolParser


class TrendyolScraper:

    def scrape(self, url: str):

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0 Safari/537.36"
            )
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        print("HTTP:", response.status_code)

        html = HTMLParser(response.text)

        print("Sayfa uzunluğu:", len(response.text))

        with open("page.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        print("HTML kaydedildi.")

        title = html.css_first("title")

        if title:
            print("Başlık:", title.text())

        if '"product"' in response.text:
            print("Product verisi bulundu.")

        if '"price"' in response.text:
            print("Price verisi bulundu.")

        if '"rating"' in response.text:
            print("Rating verisi bulundu.")

        # Parser çalıştır
        parser = TrendyolParser()

        product = parser.parse(
            response.text,
            url
        )

        print(product)

        return product