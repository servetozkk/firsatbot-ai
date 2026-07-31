from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from html import unescape
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from app.category_scrapers.base import (
    BaseCategoryScraper,
    CategoryProductLink,
    CategoryScrapeResult,
)

from app.utils.price_normalizer import PriceNormalizer


class HepsiburadaCategoryScraper(BaseCategoryScraper):
    """Hepsiburada kategori ve arama sayfalarından ürün bağlantıları toplar.

    Hepsiburada sayfa yapısını zaman zaman değiştirdiği için bağlantılar yalnızca
    tek bir CSS seçicisinden değil; görünür bağlantılardan ve sayfadaki JSON/script
    içeriklerinden birlikte çıkarılır.
    """

    store_code = "hepsiburada"
    store_name = "Hepsiburada"
    supported_domains = ("hepsiburada.com",)
    base_url = "https://www.hepsiburada.com"

    PRODUCT_CODE_PATTERN = re.compile(
        r"(?:-p-|/p/)(?:[a-z0-9-]*)(?:hb[a-z]{1,6}|hbcv|hbv|hbp)[a-z0-9-]*",
        re.IGNORECASE,
    )
    ABSOLUTE_URL_PATTERN = re.compile(
        r"https?://(?:www\.)?hepsiburada\.com/[^\s\"'<>\\]+",
        re.IGNORECASE,
    )
    RELATIVE_URL_PATTERN = re.compile(
        r"(?:\"|')(?P<url>/[^\"']+(?:-p-|/p/)[^\"']+)(?:\"|')",
        re.IGNORECASE,
    )

    @staticmethod
    def _page_url(category_url: str, page_number: int) -> str:
        parts = urlsplit(category_url)
        query_pairs = dict(parse_qsl(parts.query, keep_blank_values=True))
        if page_number > 1:
            query_pairs["sayfa"] = str(page_number)
        else:
            query_pairs.pop("sayfa", None)
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_pairs),
            "",
        ))

    @classmethod
    def _looks_like_product_url(cls, url: str) -> bool:
        parts = urlsplit(str(url or "").strip())
        hostname = (parts.hostname or "").lower()
        if not (
            hostname == "hepsiburada.com"
            or hostname.endswith(".hepsiburada.com")
        ):
            return False

        path = (parts.path or "").lower()
        if not path or path in {"/", "/ara"}:
            return False
        return bool(cls.PRODUCT_CODE_PATTERN.search(path))

    @classmethod
    def extract_product_urls_from_html(cls, html: str) -> list[str]:
        """HTML veya gömülü JSON içinden sıralı, benzersiz ürün URL'leri çıkarır."""

        source = unescape(str(html or ""))
        # JSON scriptlerinde bağlantılar çoğunlukla \/ biçiminde bulunur.
        source = source.replace("\\/", "/").replace("\\u002F", "/")

        candidates: list[str] = []
        candidates.extend(cls.ABSOLUTE_URL_PATTERN.findall(source))
        candidates.extend(
            match.group("url")
            for match in cls.RELATIVE_URL_PATTERN.finditer(source)
        )

        # Bazı Next/Redux verilerinde URL JSON değeri olarak kaçışlı gelebilir.
        for script_match in re.finditer(
            r"<(?:script|template)[^>]*>(.*?)</(?:script|template)>",
            source,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            script_text = script_match.group(1).strip()
            if not script_text or script_text[0:1] not in {"{", "["}:
                continue
            try:
                payload = json.loads(script_text)
            except (json.JSONDecodeError, TypeError):
                continue
            candidates.extend(cls._walk_json_for_urls(payload))

        result: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            cleaned_candidate = str(candidate or "").strip().rstrip(
                "\\\"'.,;)]}"
            )
            full_url = cls.clean_product_url(
                urljoin(cls.base_url, cleaned_candidate)
            )
            if not cls._looks_like_product_url(full_url):
                continue
            if full_url in seen:
                continue
            seen.add(full_url)
            result.append(full_url)
        return result

    @classmethod
    def _walk_json_for_urls(cls, value: object) -> list[str]:
        urls: list[str] = []
        if isinstance(value, dict):
            for key, item in value.items():
                normalized_key = str(key).lower()
                if isinstance(item, str) and any(
                    token in normalized_key
                    for token in ("url", "link", "href", "product")
                ):
                    urls.append(item)
                urls.extend(cls._walk_json_for_urls(item))
        elif isinstance(value, list):
            for item in value:
                urls.extend(cls._walk_json_for_urls(item))
        return urls

    @staticmethod
    def _parse_price(value: object) -> float | None:
        return PriceNormalizer.normalize(value)

    @classmethod
    def _extract_product_code(cls, url: str) -> str | None:
        match = re.search(r"(?:-p-|/p/)([^/?#]+)", str(url or ""), re.I)
        return match.group(1).upper() if match else None

    @classmethod
    def extract_product_cards_from_payload(
        cls,
        payload: list[dict[str, object]],
        *,
        category_url: str,
        page_number: int,
    ) -> list[CategoryProductLink]:
        # Tarayıcıdan alınan liste kartlarını temiz ve benzersiz tekliflere çevirir.
        results: list[CategoryProductLink] = []
        seen: set[str] = set()
        for raw in payload:
            url = cls.clean_product_url(urljoin(cls.base_url, str(raw.get("url") or "")))
            if not cls._looks_like_product_url(url) or url in seen:
                continue
            name = re.sub(r"\s+", " ", str(raw.get("name") or "")).strip()
            candidates = raw.get("price_candidates") or []
            if not isinstance(candidates, list):
                candidates = [candidates]
            explicit_price = raw.get("price")
            if explicit_price not in (None, ""):
                candidates.insert(0, explicit_price)
            price, detected_old_price = PriceNormalizer.select_offer_prices(
                candidates,
                fallback=raw.get("card_text"),
            )
            if not name or price is None:
                continue
            image = str(raw.get("image") or "").strip() or None
            if image:
                image = urljoin(cls.base_url, image)
            seen.add(url)
            results.append(CategoryProductLink(
                url=url,
                source_site=cls.store_code,
                category_url=category_url,
                page_number=page_number,
                name=name,
                price=price,
                old_price=cls._parse_price(raw.get("old_price")) or detected_old_price,
                image=image,
                seller=str(raw.get("seller") or cls.store_name).strip() or cls.store_name,
                stock_status="in_stock",
                product_code=cls._extract_product_code(url),
            ))
        return results

    @classmethod
    def _collect_product_cards(cls, page: Page, category_url: str, page_number: int) -> list[CategoryProductLink]:
        # Farklı Hepsiburada arayüzlerinden ürün kartlarını akıllı şekilde toplar.
        payload = page.locator("a[href]").evaluate_all(
            r'''elements => {
                const productPattern = /(?:-p-|\/p\/)(?:[a-z0-9-]*)(?:hb[a-z]{1,6}|hbcv|hbv|hbp)[a-z0-9-]*/i;
                const currencyPricePattern = /(?:₺|\bTL\b|\bTRY\b)\s*([0-9][0-9\s.,]*)|([0-9][0-9\s.,]*)\s*(?:₺|\bTL\b|\bTRY\b)/gi;
                const clean = value => (value || '').replace(/\s+/g, ' ').trim();
                const attr = (node, names) => {
                    for (const name of names) {
                        const value = node?.getAttribute?.(name);
                        if (value) return value;
                    }
                    return '';
                };
                const out = [];
                const seen = new Set();
                for (const a of elements) {
                    const href = a.href || a.getAttribute('href') || '';
                    if (!productPattern.test(href) || seen.has(href)) continue;
                    const card = a.closest([
                        'li', 'article', '[data-test-id*="product"]',
                        '[data-test-id*="product-card"]', '[data-testid*="product"]',
                        '[class*="productListContent"]', '[class*="productCard"]',
                        '[class*="product-card"]', '[class*="ProductCard"]',
                        '[class*="product-item"]', '[class*="productItem"]'
                    ].join(',')) || a.parentElement?.parentElement || a.parentElement;
                    if (!card) continue;
                    const text = clean(card.innerText || a.innerText || '');
                    const img = card.querySelector('img');
                    const nameNode = card.querySelector([
                        '[data-test-id*="product-name"]', '[data-testid*="product-name"]',
                        '[class*="productName"]', '[class*="product-name"]',
                        '[class*="title"]', '[class*="name"]', 'h2', 'h3'
                    ].join(','));
                    const priceNodes = [...card.querySelectorAll([
                        '[data-test-id*="price"]', '[data-testid*="price"]',
                        '[data-price]', '[itemprop="price"]',
                        '[class*="price"]', '[class*="Price"]'
                    ].join(','))];
                    const name = clean(
                        nameNode?.innerText || attr(a, ['title', 'aria-label']) ||
                        attr(img, ['alt', 'title']) || a.innerText
                    );
                    const priceCandidates = [];
                    for (const node of priceNodes) {
                        for (const value of [
                            node.innerText, node.textContent,
                            attr(node, ['data-price', 'content', 'aria-label', 'title'])
                        ]) {
                            const cleaned = clean(value);
                            if (cleaned) priceCandidates.push(cleaned);
                        }
                    }
                    if (!priceCandidates.length) {
                        const currencyMatches = [...text.matchAll(currencyPricePattern)]
                            .map(m => clean(m[0]));
                        priceCandidates.push(...currencyMatches);
                    }
                    const image = img?.currentSrc || img?.src || attr(img, ['data-src', 'data-original', 'data-lazy-src']);
                    out.push({
                        url: href,
                        name,
                        price_candidates: [...new Set(priceCandidates)],
                        card_text: text,
                        image,
                        seller: 'Hepsiburada'
                    });
                    seen.add(href);
                }
                return out;
            }'''
        )
        cards = cls.extract_product_cards_from_payload(
            payload,
            category_url=category_url,
            page_number=page_number,
        )
        if cards:
            return cards

        # DOM kartları değiştiğinde JSON-LD / Next.js / Redux verileri yedek olur.
        return cls.extract_product_cards_from_html(
            page.content(),
            category_url=category_url,
            page_number=page_number,
        )

    @classmethod
    def extract_product_cards_from_html(
        cls,
        html: str,
        *,
        category_url: str,
        page_number: int,
    ) -> list[CategoryProductLink]:
        source = unescape(str(html or '')).replace('\\/', '/').replace('\\u002F', '/')
        payloads: list[dict[str, object]] = []

        def visit(value: object) -> None:
            if isinstance(value, dict):
                lowered = {str(k).lower(): v for k, v in value.items()}
                url = next((lowered.get(k) for k in ('url', 'producturl', 'product_url', 'link', 'href') if lowered.get(k)), None)
                name = next((lowered.get(k) for k in ('name', 'title', 'productname', 'product_name') if lowered.get(k)), None)
                image = next((lowered.get(k) for k in ('image', 'imageurl', 'image_url', 'thumbnail') if lowered.get(k)), None)
                price = next((lowered.get(k) for k in ('price', 'currentprice', 'saleprice', 'discountedprice') if lowered.get(k) is not None), None)
                offers = lowered.get('offers')
                if isinstance(offers, dict):
                    price = price if price is not None else offers.get('price') or offers.get('lowPrice')
                    url = url or offers.get('url')
                if isinstance(url, str) and cls._looks_like_product_url(urljoin(cls.base_url, url)):
                    payloads.append({'url': url, 'name': name, 'price': price, 'image': image, 'seller': cls.store_name})
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        for match in re.finditer(r'<script[^>]*>(.*?)</script>', source, flags=re.I | re.S):
            text = match.group(1).strip()
            if not text or text[:1] not in {'{', '['}:
                continue
            try:
                visit(json.loads(text))
            except (json.JSONDecodeError, TypeError, RecursionError):
                continue

        return cls.extract_product_cards_from_payload(
            payloads,
            category_url=category_url,
            page_number=page_number,
        )

    @classmethod
    def _save_debug_artifacts(cls, page: Page, page_number: int, reason: str) -> Path | None:
        if os.getenv('SCRAPER_DEBUG', 'true').strip().lower() not in {'1', 'true', 'yes', 'on'}:
            return None
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        directory = Path('debug') / 'hepsiburada' / f'{stamp}_sayfa_{page_number}'
        try:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / 'page.html').write_text(page.content(), encoding='utf-8')
            (directory / 'meta.json').write_text(json.dumps({
                'url': page.url,
                'title': page.title(),
                'reason': reason,
                'saved_at': datetime.now().isoformat(timespec='seconds'),
            }, ensure_ascii=False, indent=2), encoding='utf-8')
            page.screenshot(path=str(directory / 'page.png'), full_page=True)
            return directory
        except Exception as error:
            print('Hepsiburada debug çıktısı kaydedilemedi:', type(error).__name__, error)
            return None

    @staticmethod
    def _launch_browser(playwright: Playwright) -> Browser:
        """Önce sistem Chrome'unu, yoksa Playwright Chromium'u kullanır."""

        try:
            return playwright.chromium.launch(
                headless=True,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            return playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )

    @staticmethod
    def _scroll_page(page: Page) -> None:
        previous_height = 0
        for _ in range(12):
            page.mouse.wheel(0, 1900)
            page.wait_for_timeout(650)
            height = int(page.evaluate("document.body.scrollHeight") or 0)
            if height == previous_height:
                break
            previous_height = height

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
            browser = self._launch_browser(playwright)
            context = browser.new_context(
                locale="tr-TR",
                timezone_id="Europe/Istanbul",
                viewport={"width": 1440, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                extra_http_headers={
                    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Referer": "https://www.hepsiburada.com/",
                },
            )
            page = context.new_page()

            try:
                for page_number in range(1, max_pages + 1):
                    page_url = self._page_url(category_url, page_number)
                    print(
                        f"Hepsiburada kategori sayfası {page_number}: {page_url}"
                    )

                    response = page.goto(
                        page_url,
                        wait_until="domcontentloaded",
                        timeout=75_000,
                    )
                    if response is not None and response.status >= 400:
                        result.warnings.append(
                            f"{page_number}. sayfa HTTP {response.status} döndürdü."
                        )
                        break

                    page.wait_for_timeout(4000)
                    self._scroll_page(page)

                    title = (page.title() or "").lower()
                    body_text = (
                        page.locator("body").inner_text(timeout=10_000) or ""
                    ).lower()
                    if any(
                        token in f"{title} {body_text[:2500]}"
                        for token in (
                            "güvenlik kontrolü",
                            "security check",
                            "captcha",
                            "robot olmadığınızı",
                        )
                    ):
                        result.warnings.append(
                            "Hepsiburada güvenlik doğrulaması gösterdi. "
                            "Tarama daha sonra yeniden denenebilir."
                        )
                        break

                    before = len(seen)

                    # V3: Ürün adı, fiyat ve görseli kategori kartından toplar.
                    # Böylece Hepsiburada ürün detay sayfasını açmaya gerek kalmaz.
                    cards = self._collect_product_cards(
                        page, category_url, page_number
                    )
                    if not cards:
                        debug_dir = self._save_debug_artifacts(
                            page, page_number, "Ürün kartı adı ve fiyatıyla bulunamadı."
                        )
                        if debug_dir:
                            result.warnings.append(
                                f"Ürün kartları okunamadı. Debug çıktısı: {debug_dir}"
                            )
                            print(f"Hepsiburada debug çıktısı kaydedildi: {debug_dir}")
                    for card in cards:
                        if card.url in seen:
                            continue
                        seen.add(card.url)
                        result.links.append(card)
                        if len(result.links) >= limit:
                            break

                    # Kart yapısı değişirse URL keşfini korur. Fiyatı olmayan
                    # kayıtlar Discovery Service tarafından hızlıca atlanır.
                    if len(result.links) < limit:
                        extracted = self.extract_product_urls_from_html(page.content())
                        for href in extracted:
                            full_url = self.clean_product_url(urljoin(self.base_url, str(href)))
                            if not self._looks_like_product_url(full_url) or full_url in seen:
                                continue
                            seen.add(full_url)
                            result.links.append(CategoryProductLink(
                                url=full_url,
                                source_site=self.store_code,
                                category_url=category_url,
                                page_number=page_number,
                                product_code=self._extract_product_code(full_url),
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
