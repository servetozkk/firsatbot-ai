from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from playwright.sync_api import sync_playwright
from selectolax.parser import HTMLParser

from app.parsers.trendyol_parser import TrendyolParser


class TrendyolScraper:
    BASE_URL = "https://www.trendyol.com"

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0 Safari/537.36"
            )
        }

    @staticmethod
    def clean_product_url(url: str) -> str:
        """
        Ürün bağlantısındaki gereksiz sorgu parametrelerini temizler.
        Böylece aynı ürünün farklı takip bağlantıları tek URL olur.
        """
        parts = urlsplit(url)

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                "",
                "",
            )
        )

    def scrape(self, url: str):
        """
        Tek bir Trendyol ürün sayfasını okur.
        Mevcut sistemle uyumludur.
        """
        response = requests.get(
            url,
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()

        print("HTTP:", response.status_code)
        print("Sayfa uzunluğu:", len(response.text))

        parser = TrendyolParser()

        product = parser.parse(
            response.text,
            url,
        )

        return product

    def get_product_links(
        self,
        category_url: str,
        limit: int = 10,
    ) -> list[str]:
        """
        Trendyol kategori veya arama sayfasından ürün bağlantılarını çıkarır.
        """
        product_links: list[str] = []
        seen_links: set[str] = set()

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
            )

            page = browser.new_page(
                user_agent=self.headers["User-Agent"],
                viewport={
                    "width": 1440,
                    "height": 1200,
                },
                locale="tr-TR",
            )

            try:
                print("Kategori açılıyor:", category_url)

                page.goto(
                    category_url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                page.wait_for_timeout(4000)

                # Sayfanın biraz aşağı kaydırılması, ürünlerin yüklenmesine
                # yardımcı olur.
                for _ in range(5):
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(1000)

                anchors = page.locator("a[href*='-p-']")
                anchor_count = anchors.count()

                print("Bulunan ürün bağlantısı adayı:", anchor_count)

                for index in range(anchor_count):
                    href = anchors.nth(index).get_attribute("href")

                    if not href:
                        continue

                    full_url = urljoin(
                        self.BASE_URL,
                        href,
                    )

                    clean_url = self.clean_product_url(full_url)

                    if clean_url in seen_links:
                        continue

                    seen_links.add(clean_url)
                    product_links.append(clean_url)

                    if len(product_links) >= limit:
                        break

            finally:
                browser.close()

        print("Benzersiz ürün bağlantısı:", len(product_links))

        return product_links

    def scrape_category(
        self,
        category_url: str,
        limit: int = 10,
    ):
        """
        Kategoriden ürün linklerini alır ve her ürünü mevcut parser ile okur.
        """
        links = self.get_product_links(
            category_url=category_url,
            limit=limit,
        )

        products = []

        for number, product_url in enumerate(links, start=1):
            print()
            print(f"[{number}/{len(links)}] Ürün okunuyor:")
            print(product_url)

            try:
                product = self.scrape(product_url)

                if product is None:
                    print("Ürün bilgisi okunamadı.")
                    continue

                products.append(product)
                print("Ürün bulundu:", product.name)

            except Exception as error:
                print("Ürün okuma hatası:", error)

        return products

