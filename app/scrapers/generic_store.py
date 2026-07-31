from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
from selectolax.parser import HTMLParser

from app.models.product import Product
from app.parsers.base_parser import BaseParser
from app.scrapers.base import BaseScraper
from app.services.browser_engine import BrowserEngine


@dataclass(frozen=True)
class GenericStoreConfig:
    code: str
    name: str
    domains: tuple[str, ...]
    title_selectors: tuple[str, ...] = ()
    price_selectors: tuple[str, ...] = ()
    old_price_selectors: tuple[str, ...] = ()
    seller_selectors: tuple[str, ...] = ()
    image_selectors: tuple[str, ...] = ()
    rating_selectors: tuple[str, ...] = ()
    review_selectors: tuple[str, ...] = ()
    stock_selectors: tuple[str, ...] = ()
    product_code_selectors: tuple[str, ...] = ()


class GenericStoreScraper(BaseScraper):
    """JSON-LD ve CSS seçicileriyle çalışan ortak mağaza scraper'ı."""

    def __init__(self, config: GenericStoreConfig) -> None:
        super().__init__(config.name)
        self.config = config
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        project_root = Path(__file__).resolve().parents[2]
        self.browser_engine = BrowserEngine(
            profile_directory=project_root / f".playwright-{config.code}-profile",
            locale="tr-TR",
            headless=True,
            channel="chrome",
            viewport_width=1440,
            viewport_height=1000,
            accept_language=self.headers["Accept-Language"],
        )

    def _validate_url(self, url: str) -> str:
        normalized = str(url or "").strip()
        if not normalized:
            raise ValueError(f"{self.config.name} ürün bağlantısı boş.")
        if not normalized.startswith(("http://", "https://")):
            normalized = f"https://{normalized}"
        hostname = (urlsplit(normalized).hostname or "").lower()
        if not any(hostname == d or hostname.endswith(f".{d}") for d in self.config.domains):
            raise ValueError(f"Bağlantı {self.config.name} alan adına ait değil.")
        return normalized

    def _download(self, url: str) -> str:
        try:
            response = requests.get(url, headers=self.headers, timeout=25, allow_redirects=True)
            response.raise_for_status()
            html = response.text
            if len(html) >= 5000 and "captcha" not in html.lower():
                return html
        except requests.RequestException:
            pass

        # Ortak BrowserEngine'in kullandığı metot sürüme göre farklı olabilir.
        for method_name in ("get_page_content", "fetch_html", "get_html", "load"):
            method = getattr(self.browser_engine, method_name, None)
            if callable(method):
                result = method(url)
                if isinstance(result, str) and result.strip():
                    return result
        raise RuntimeError(f"{self.config.name} ürün sayfası indirilemedi.")

    @staticmethod
    def _first_text(tree: HTMLParser, selectors: tuple[str, ...]) -> str | None:
        for selector in selectors:
            node = tree.css_first(selector)
            if node:
                value = node.text(strip=True)
                if value:
                    return value
                for attr in ("content", "value", "data-price"):
                    candidate = node.attributes.get(attr)
                    if candidate:
                        return candidate.strip()
        return None

    @staticmethod
    def _first_attr(tree: HTMLParser, selectors: tuple[str, ...], attrs: tuple[str, ...]) -> str | None:
        for selector in selectors:
            node = tree.css_first(selector)
            if not node:
                continue
            for attr in attrs:
                value = node.attributes.get(attr)
                if value:
                    return value.strip()
        return None

    @staticmethod
    def _jsonld_nodes(tree: HTMLParser) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for script in tree.css('script[type="application/ld+json"]'):
            raw = script.text(strip=True)
            if not raw:
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                continue
            stack = value if isinstance(value, list) else [value]
            while stack:
                item = stack.pop(0)
                if isinstance(item, dict):
                    graph = item.get("@graph")
                    if isinstance(graph, list):
                        stack.extend(graph)
                    nodes.append(item)
                elif isinstance(item, list):
                    stack.extend(item)
        return nodes

    @classmethod
    def _find_product_node(cls, tree: HTMLParser) -> dict[str, Any]:
        for node in cls._jsonld_nodes(tree):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if any(str(item).lower() == "product" for item in types if item):
                return node
        return {}

    @staticmethod
    def _offer(product_node: dict[str, Any]) -> dict[str, Any]:
        offers = product_node.get("offers") or {}
        if isinstance(offers, list):
            return next((item for item in offers if isinstance(item, dict)), {})
        return offers if isinstance(offers, dict) else {}

    @staticmethod
    def _brand(product_node: dict[str, Any]) -> str | None:
        brand = product_node.get("brand")
        if isinstance(brand, dict):
            return BaseParser._clean_text(brand.get("name"))
        return BaseParser._clean_text(brand)

    def scrape(self, url: str) -> Product:
        normalized_url = self._validate_url(url)
        html = self._download(normalized_url)
        tree = HTMLParser(html)
        product_node = self._find_product_node(tree)
        offer = self._offer(product_node)

        name = BaseParser._clean_text(product_node.get("name")) or self._first_text(tree, self.config.title_selectors)
        price = BaseParser._parse_price(
            offer.get("price") or offer.get("lowPrice") or self._first_text(tree, self.config.price_selectors)
        )
        old_price = BaseParser._parse_price(self._first_text(tree, self.config.old_price_selectors))

        aggregate = product_node.get("aggregateRating") or {}
        if not isinstance(aggregate, dict):
            aggregate = {}
        rating = BaseParser._parse_float(aggregate.get("ratingValue") or self._first_text(tree, self.config.rating_selectors))
        review_count = BaseParser._parse_int(
            aggregate.get("reviewCount") or aggregate.get("ratingCount") or self._first_text(tree, self.config.review_selectors)
        )

        seller_data = offer.get("seller") or product_node.get("seller") or {}
        seller = None
        if isinstance(seller_data, dict):
            seller = BaseParser._clean_text(seller_data.get("name"))
        elif seller_data:
            seller = BaseParser._clean_text(seller_data)
        seller = seller or self._first_text(tree, self.config.seller_selectors) or self.config.name

        image = product_node.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        elif isinstance(image, dict):
            image = image.get("url") or image.get("contentUrl")
        image = BaseParser._clean_text(image) or self._first_attr(tree, self.config.image_selectors, ("src", "data-src", "content"))

        availability = BaseParser._clean_text(offer.get("availability"))
        stock = self._first_text(tree, self.config.stock_selectors)
        if availability:
            stock = "Stokta" if "instock" in availability.lower() else availability.rsplit("/", 1)[-1]

        product_code = BaseParser._clean_text(
            product_node.get("sku") or product_node.get("mpn") or product_node.get("gtin13") or product_node.get("gtin")
        ) or self._first_text(tree, self.config.product_code_selectors)

        if not name:
            raise ValueError(f"{self.config.name} ürün adı bulunamadı.")
        if not price:
            raise ValueError(f"{self.config.name} güncel fiyatı bulunamadı.")

        return Product(
            name=name,
            price=price,
            old_price=old_price,
            rating=rating,
            review_count=review_count,
            seller=seller,
            url=normalized_url,
            image=image,
            brand=self._brand(product_node),
            model=BaseParser._clean_text(product_node.get("model")),
            category=BaseParser._clean_text(product_node.get("category")),
            description=BaseParser._clean_description(product_node.get("description")),
            specifications=None,
            stock_status=stock,
            source_site=self.config.name,
            product_code=product_code,
        )
