from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True, slots=True)
class CategoryProductLink:
    url: str
    source_site: str
    category_url: str
    page_number: int = 1
    name: str | None = None
    price: float | None = None
    old_price: float | None = None
    image: str | None = None
    seller: str | None = None
    brand: str | None = None
    stock_status: str | None = None
    product_code: str | None = None

    @property
    def has_list_offer(self) -> bool:
        return bool(self.name and self.price is not None and self.price > 0)


@dataclass(slots=True)
class CategoryScrapeResult:
    store_code: str
    store_name: str
    category_url: str
    links: list[CategoryProductLink] = field(default_factory=list)
    visited_page_count: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def found_count(self) -> int:
        return len(self.links)


class BaseCategoryScraper(ABC):
    store_code: str
    store_name: str
    supported_domains: tuple[str, ...]

    def supports_url(self, url: str) -> bool:
        hostname = (urlsplit(self.normalize_url(url)).hostname or "").lower()
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in self.supported_domains
        )

    @staticmethod
    def normalize_url(url: str) -> str:
        normalized = str(url or "").strip()
        if not normalized:
            raise ValueError("Kategori bağlantısı boş olamaz.")
        if not normalized.startswith(("http://", "https://")):
            normalized = f"https://{normalized}"
        parts = urlsplit(normalized)
        if not parts.hostname:
            raise ValueError("Geçerli bir kategori bağlantısı girilmedi.")
        return urlunsplit(("https", parts.netloc.lower(), parts.path or "/", parts.query, ""))

    @staticmethod
    def clean_product_url(url: str) -> str:
        parts = urlsplit(str(url or "").strip())
        return urlunsplit(("https", parts.netloc.lower(), parts.path, "", ""))

    @abstractmethod
    def collect_product_links(
        self,
        category_url: str,
        limit: int = 100,
        max_pages: int = 10,
    ) -> CategoryScrapeResult:
        """Kategori sayfalarından benzersiz ürün bağlantıları toplar."""
        raise NotImplementedError
