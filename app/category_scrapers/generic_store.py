from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.category_scrapers.base import BaseCategoryScraper, CategoryProductLink, CategoryScrapeResult


@dataclass(frozen=True, slots=True)
class GenericCategoryConfig:
    code: str
    name: str
    domains: tuple[str, ...]
    base_url: str
    product_url_markers: tuple[str, ...]
    product_link_selectors: tuple[str, ...]
    card_selectors: tuple[str, ...] = ()
    title_selectors: tuple[str, ...] = ("h2", "h3", "[data-testid*='title']", "[class*='title']")
    price_selectors: tuple[str, ...] = ("[data-testid*='price']", "[class*='price']")
    image_selectors: tuple[str, ...] = ("img",)
    page_param: str = "page"
    first_page_value: int = 1
    page_value_offset: int = 0
    scroll_rounds: int = 8
    wait_ms: int = 2200


class GenericCategoryScraper(BaseCategoryScraper):
    """Çok mağazalı kategori bağlantısı toplayıcı.

    Önce ürün kartlarından zengin veri toplamayı dener. Kart yapısı değişmişse
    tüm ürün linklerini ve JSON-LD ItemList kayıtlarını yedek olarak kullanır.
    """

    def __init__(self, config: GenericCategoryConfig) -> None:
        self.config = config
        self.store_code = config.code
        self.store_name = config.name
        self.supported_domains = config.domains

    def _page_url(self, category_url: str, page_number: int) -> str:
        if page_number <= 1:
            return category_url
        parts = urlsplit(category_url)
        pairs = dict(parse_qsl(parts.query, keep_blank_values=True))
        pairs[self.config.page_param] = str(
            self.config.first_page_value + (page_number - 1) + self.config.page_value_offset
        )
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(pairs), ""))

    def _looks_like_product_url(self, url: str) -> bool:
        path = (urlsplit(url).path or "").lower()
        return any(marker.lower() in path for marker in self.config.product_url_markers)

    @staticmethod
    def _clean_text(value: object) -> str | None:
        text = " ".join(str(value or "").split()).strip()
        return text or None

    @staticmethod
    def _parse_price(value: object) -> float | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        import re
        match = re.search(r"(\d[\d\s\.]*[\.,]\d{2}|\d[\d\s\.]*)", raw)
        if not match:
            return None
        number = match.group(1).replace(" ", "")
        if "," in number:
            number = number.replace(".", "").replace(",", ".")
        elif number.count(".") > 1:
            number = number.replace(".", "")
        try:
            result = float(number)
            return result if result > 0 else None
        except ValueError:
            return None

    def _jsonld_links(self, page) -> list[str]:
        script_values = page.locator('script[type="application/ld+json"]').all_text_contents()
        output: list[str] = []
        for raw in script_values:
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            stack = data if isinstance(data, list) else [data]
            while stack:
                item = stack.pop(0)
                if isinstance(item, list):
                    stack.extend(item)
                    continue
                if not isinstance(item, dict):
                    continue
                graph = item.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
                entries = item.get("itemListElement")
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict):
                            candidate = entry.get("url")
                            nested = entry.get("item")
                            if isinstance(nested, dict):
                                candidate = candidate or nested.get("url")
                            if candidate:
                                output.append(str(candidate))
        return output

    def _collect_card_rows(self, page, category_url: str, page_number: int) -> list[CategoryProductLink]:
        if not self.config.card_selectors:
            return []
        for card_selector in self.config.card_selectors:
            cards = page.locator(card_selector)
            count = min(cards.count(), 300)
            if count <= 0:
                continue
            rows: list[CategoryProductLink] = []
            for index in range(count):
                card = cards.nth(index)
                href = None
                for selector in self.config.product_link_selectors:
                    node = card.locator(selector).first
                    if node.count():
                        href = node.get_attribute("href")
                        if href:
                            break
                if not href:
                    continue
                full_url = self.clean_product_url(urljoin(self.config.base_url, href))
                if not self._looks_like_product_url(full_url):
                    continue
                title = None
                for selector in self.config.title_selectors:
                    node = card.locator(selector).first
                    if node.count():
                        title = self._clean_text(node.get_attribute("title") or node.inner_text())
                        if title:
                            break
                price = None
                for selector in self.config.price_selectors:
                    node = card.locator(selector).first
                    if node.count():
                        price = self._parse_price(
                            node.get_attribute("content")
                            or node.get_attribute("data-price")
                            or node.inner_text()
                        )
                        if price:
                            break
                image = None
                for selector in self.config.image_selectors:
                    node = card.locator(selector).first
                    if node.count():
                        image = (
                            node.get_attribute("src")
                            or node.get_attribute("data-src")
                            or node.get_attribute("data-original")
                        )
                        if image:
                            image = urljoin(self.config.base_url, image)
                            break
                rows.append(CategoryProductLink(
                    url=full_url,
                    source_site=self.store_code,
                    category_url=category_url,
                    page_number=page_number,
                    name=title,
                    price=price,
                    image=image,
                    seller=self.store_name,
                ))
            if rows:
                return rows
        return []

    def collect_product_links(self, category_url: str, limit: int = 100, max_pages: int = 10) -> CategoryScrapeResult:
        category_url = self.normalize_url(category_url)
        limit = max(1, min(int(limit or 100), 5000))
        max_pages = max(1, min(int(max_pages or 10), 200))
        result = CategoryScrapeResult(
            store_code=self.store_code,
            store_name=self.store_name,
            category_url=category_url,
        )
        seen: set[str] = set()

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, channel="chrome")
            context = browser.new_context(
                locale="tr-TR",
                viewport={"width": 1440, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                extra_http_headers={
                    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Cache-Control": "no-cache",
                },
            )
            page = context.new_page()
            try:
                for page_number in range(1, max_pages + 1):
                    page_url = self._page_url(category_url, page_number)
                    try:
                        response = page.goto(page_url, wait_until="domcontentloaded", timeout=75_000)
                    except PlaywrightTimeoutError:
                        result.warnings.append(f"{page_number}. sayfa zaman aşımına uğradı.")
                        break
                    if response is not None and response.status >= 400:
                        result.warnings.append(f"{page_number}. sayfa HTTP {response.status} döndürdü.")
                        break
                    page.wait_for_timeout(self.config.wait_ms)
                    previous_height = 0
                    for _ in range(self.config.scroll_rounds):
                        page.mouse.wheel(0, 1800)
                        page.wait_for_timeout(500)
                        height = page.evaluate("document.body.scrollHeight")
                        if height == previous_height:
                            break
                        previous_height = height

                    before = len(seen)
                    card_rows = self._collect_card_rows(page, category_url, page_number)
                    candidates: list[CategoryProductLink] = card_rows
                    if not candidates:
                        hrefs: list[str] = []
                        for selector in self.config.product_link_selectors:
                            hrefs.extend(page.locator(selector).evaluate_all(
                                "(els) => els.map((el) => el.getAttribute('href')).filter(Boolean)"
                            ))
                        hrefs.extend(self._jsonld_links(page))
                        candidates = [CategoryProductLink(
                            url=self.clean_product_url(urljoin(self.config.base_url, href)),
                            source_site=self.store_code,
                            category_url=category_url,
                            page_number=page_number,
                        ) for href in hrefs]

                    for row in candidates:
                        if not self._looks_like_product_url(row.url) or row.url in seen:
                            continue
                        seen.add(row.url)
                        result.links.append(row)
                        if len(result.links) >= limit:
                            break

                    result.visited_page_count += 1
                    if len(result.links) >= limit:
                        break
                    if len(seen) == before:
                        break
            finally:
                context.close()
                browser.close()
        return result
