from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

from app.category_scrapers.base import (
    BaseCategoryScraper,
    CategoryProductLink,
    CategoryScrapeResult,
)


class TrendyolCategoryScraper(BaseCategoryScraper):
    store_code = "trendyol"
    store_name = "Trendyol"
    supported_domains = ("trendyol.com",)
    base_url = "https://www.trendyol.com"

    @staticmethod
    def _page_url(category_url: str, page_number: int) -> str:
        parts = urlsplit(category_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        if page_number > 1:
            query["pi"] = str(page_number)
        else:
            query.pop("pi", None)
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            "",
        ))

    def collect_product_links(
        self,
        category_url: str,
        limit: int = 100,
        max_pages: int = 10,
    ) -> CategoryScrapeResult:
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
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                locale="tr-TR",
                viewport={"width": 1440, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            try:
                for page_number in range(1, max_pages + 1):
                    page_url = self._page_url(category_url, page_number)
                    print(f"Trendyol kategori sayfası {page_number}: {page_url}")

                    response = page.goto(
                        page_url,
                        wait_until="domcontentloaded",
                        timeout=60_000,
                    )
                    if response is not None and response.status >= 400:
                        result.warnings.append(
                            f"{page_number}. sayfa HTTP {response.status} döndürdü."
                        )
                        break

                    page.wait_for_timeout(2500)
                    previous_height = 0
                    for _ in range(8):
                        page.mouse.wheel(0, 1800)
                        page.wait_for_timeout(500)
                        height = page.evaluate("document.body.scrollHeight")
                        if height == previous_height:
                            break
                        previous_height = height

                    hrefs = page.locator("a[href*='-p-']").evaluate_all(
                        "(els) => els.map((el) => el.getAttribute('href')).filter(Boolean)"
                    )

                    before = len(seen)
                    for href in hrefs:
                        full_url = self.clean_product_url(urljoin(self.base_url, href))
                        if full_url in seen:
                            continue
                        seen.add(full_url)
                        result.links.append(CategoryProductLink(
                            url=full_url,
                            source_site=self.store_code,
                            category_url=category_url,
                            page_number=page_number,
                        ))
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
