from __future__ import annotations

from app.category_scrapers.base import BaseCategoryScraper
from app.category_scrapers.hepsiburada import HepsiburadaCategoryScraper
from app.category_scrapers.teknosa import TeknosaCategoryScraper
from app.category_scrapers.trendyol import TrendyolCategoryScraper


class UnsupportedCategoryStoreError(ValueError):
    pass


class CategoryScraperRegistry:
    def __init__(self) -> None:
        self._scrapers: tuple[BaseCategoryScraper, ...] = (
            TrendyolCategoryScraper(),
            TeknosaCategoryScraper(),
            HepsiburadaCategoryScraper(),
        )

    def get_scraper(self, category_url: str) -> BaseCategoryScraper:
        for scraper in self._scrapers:
            if scraper.supports_url(category_url):
                return scraper
        raise UnsupportedCategoryStoreError(
            "Bu kategori mağazası henüz desteklenmiyor. "
            "Şu anda Trendyol, Teknosa ve Hepsiburada kategori bağlantıları kullanılabilir."
        )

    def detect_store_code(self, category_url: str) -> str:
        return self.get_scraper(category_url).store_code

    def list_stores(self) -> list[dict[str, str]]:
        return [
            {
                "code": scraper.store_code,
                "name": scraper.store_name,
            }
            for scraper in self._scrapers
        ]
