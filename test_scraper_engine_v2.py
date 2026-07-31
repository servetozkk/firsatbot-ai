from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from unittest.mock import patch

from app.category_scrapers.base import CategoryProductLink, CategoryScrapeResult
from app.services.category_discovery_service import CategoryDiscoveryService


@dataclass
class FakeProduct:
    name: str


class FakeCategoryScraper:
    def collect_product_links(self, category_url: str, limit: int, max_pages: int):
        return CategoryScrapeResult(
            store_code="test",
            store_name="Test Store",
            category_url=category_url,
            links=[
                CategoryProductLink(url=f"https://example.com/p/{i}", source_site="Test Store", category_url=category_url)
                for i in range(6)
            ],
            visited_page_count=1,
        )


class FakeCategoryRegistry:
    def get_scraper(self, category_url: str):
        return FakeCategoryScraper()


active = 0
peak = 0
lock = threading.Lock()


def fake_scrape(url: str, retry_count: int):
    global active, peak
    with lock:
        active += 1
        peak = max(peak, active)
    time.sleep(0.08)
    with lock:
        active -= 1
    return FakeProduct(name=url.rsplit("/", 1)[-1])


service = CategoryDiscoveryService(category_registry=FakeCategoryRegistry())

with (
    patch.object(service, "_scrape_one", side_effect=fake_scrape),
    patch("app.services.category_discovery_service.save_product"),
    patch("app.services.category_discovery_service.add_product", return_value=(True, "ok")),
    patch("app.services.category_discovery_service.SCRAPER_WORKERS", 3),
    patch("app.services.category_discovery_service.SCRAPER_REQUEST_DELAY", 0.0),
):
    result = service.scan_and_save("https://example.com/category", limit=6, max_pages=1)

assert result.success
assert result.saved_count == 6
assert result.failed_count == 0
assert result.worker_count == 3
assert peak >= 2, f"Paralel çalışma görülmedi. peak={peak}"

print("KAYDEDİLEN:", result.saved_count)
print("PARALEL TEPE WORKER:", peak)
print("SCRAPER ENGINE V2 TESTLERİ BAŞARILI")
