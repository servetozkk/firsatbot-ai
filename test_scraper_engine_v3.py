from __future__ import annotations

import sys
import types

# Bu test veritabanına ihtiyaç duymadan liste-modu mimarisini doğrular.
product_config_stub = types.ModuleType("app.services.product_config_service")
product_config_stub.add_product = lambda **kwargs: (True, "eklendi")
sys.modules["app.services.product_config_service"] = product_config_stub

product_service_stub = types.ModuleType("app.services.product_service")
product_service_stub.save_product = lambda product: None
sys.modules["app.services.product_service"] = product_service_stub

scraper_registry_stub = types.ModuleType("app.services.scraper_registry")
class DummyRegistry:
    def scrape(self, url):
        raise AssertionError("Detay scraper çağrılmamalı")
scraper_registry_stub.ScraperRegistry = DummyRegistry
sys.modules["app.services.scraper_registry"] = scraper_registry_stub

runtime_stub = types.ModuleType("app.services.scraper_runtime_config")
runtime_stub.SCRAPER_REQUEST_DELAY = 0.0
runtime_stub.SCRAPER_RETRY_COUNT = 0
runtime_stub.SCRAPER_WORKERS = 3
sys.modules["app.services.scraper_runtime_config"] = runtime_stub

from app.category_scrapers.base import CategoryScrapeResult
from app.category_scrapers.hepsiburada import HepsiburadaCategoryScraper
from app.services.category_discovery_service import CategoryDiscoveryService


payload = [
    {
        "url": "https://www.hepsiburada.com/apple-iphone-15-128-gb-siyah-p-HBCV00004X9ZCH?magaza=Test",
        "name": "Apple iPhone 15 128 GB Siyah",
        "price": "48.499,00 TL",
        "old_price": "49.999,00 TL",
        "image": "https://productimages.hepsiburada.net/test.jpg",
        "seller": "Hepsiburada",
    },
    {
        "url": "https://www.hepsiburada.com/apple-iphone-15-128-gb-siyah-p-HBCV00004X9ZCH",
        "name": "Tekrar",
        "price": "48.499 TL",
    },
    {
        "url": "https://www.hepsiburada.com/samsung-galaxy-s25-fe-p-HBCV00009S5CRQ",
        "name": "Samsung Galaxy S25 FE 256 GB 8 GB RAM",
        "price": "39.750 TL",
    },
]

cards = HepsiburadaCategoryScraper.extract_product_cards_from_payload(
    payload,
    category_url="https://www.hepsiburada.com/cep-telefonlari-c-371965",
    page_number=1,
)
assert len(cards) == 2
assert cards[0].price == 48499.0
assert cards[0].old_price == 49999.0
assert cards[0].product_code == "HBCV00004X9ZCH"
assert cards[0].has_list_offer


class FakeCategoryRegistry:
    def get_scraper(self, _url):
        class FakeScraper:
            def collect_product_links(self, **_kwargs):
                return CategoryScrapeResult(
                    store_code="hepsiburada",
                    store_name="Hepsiburada",
                    category_url="https://www.hepsiburada.com/cep-telefonlari-c-371965",
                    links=cards,
                    visited_page_count=1,
                )
        return FakeScraper()


class TestService(CategoryDiscoveryService):
    def __init__(self):
        super().__init__(category_registry=FakeCategoryRegistry())
        self.products = []

    @staticmethod
    def _scrape_one(url: str, retry_count: int):
        raise AssertionError("Hepsiburada liste modunda ürün detay scraper'ı çağrılmamalı")

    def _save_scraped_product(self, *, product, url, store_name, result):
        self.products.append(product)
        result.saved_count += 1


service = TestService()
result = service.scan_and_save("https://www.hepsiburada.com/cep-telefonlari-c-371965")
assert result.success is True
assert result.saved_count == 2
assert result.list_offer_count == 2
assert result.detail_queue_count == 0
assert result.worker_count == 0
assert len(service.products) == 2
assert service.products[0].source_site == "hepsiburada"

print("KART SAYISI:", len(cards))
print("LİSTE TEKLİFİ:", result.list_offer_count)
print("DETAY KUYRUĞU:", result.detail_queue_count)
print("SCRAPER ENGINE V3 TESTLERİ BAŞARILI")
