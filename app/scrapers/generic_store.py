from __future__ import annotations

import json
import os
import shutil
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlsplit
from time import perf_counter

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selectolax.parser import HTMLParser

from app.services.product_image_service import collect_image_urls, serialize_image_gallery
from app.models.product import Product
from app.parsers.base_parser import BaseParser
from app.scrapers.base import BaseScraper
from app.services.browser_engine import BrowserEngine
from app.services.product_identity_service import ProductIdentityService


# V23.62.60: N11 detail HTTP session process scope'unda tutulur.
# Force taramalarinda scraper instance yeniden olusturulsa bile ayni Session/
# urllib3 pool yasamaya devam eder. N11 dedicated lane seri oldugu icin request
# kullanimi tek lane'de kalir; lock yalniz creation/counter metadata icindir.
_N11_DETAIL_SESSION_V236260: requests.Session | None = None
_N11_DETAIL_SESSION_REQUEST_COUNT_V236260 = 0
_N11_DETAIL_SESSION_LOCK_V236260 = threading.Lock()


def _n11_shared_detail_session_v236260(retry: Retry) -> tuple[requests.Session, int, bool]:
    global _N11_DETAIL_SESSION_V236260
    global _N11_DETAIL_SESSION_REQUEST_COUNT_V236260
    with _N11_DETAIL_SESSION_LOCK_V236260:
        reused = _N11_DETAIL_SESSION_V236260 is not None
        if _N11_DETAIL_SESSION_V236260 is None:
            session = requests.Session()
            session.mount(
                "https://",
                HTTPAdapter(
                    max_retries=retry,
                    pool_connections=2,
                    pool_maxsize=2,
                    pool_block=False,
                ),
            )
            _N11_DETAIL_SESSION_V236260 = session
        _N11_DETAIL_SESSION_REQUEST_COUNT_V236260 += 1
        return (
            _N11_DETAIL_SESSION_V236260,
            _N11_DETAIL_SESSION_REQUEST_COUNT_V236260,
            reused,
        )


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
        self._temporary_browser_profile = config.code == "mediamarkt"
        if self._temporary_browser_profile:
            profile_name = (
                f".playwright-{config.code}-runtime-"
                f"{os.getpid()}-{threading.get_ident()}-{uuid.uuid4().hex[:8]}"
            )
        else:
            profile_name = f".playwright-{config.code}-profile"
        self.browser_engine = BrowserEngine(
            profile_directory=project_root / profile_name,
            locale="tr-TR",
            headless=(config.code != "mediamarkt"),
            channel="chrome",
            viewport_width=1440,
            viewport_height=1000,
            accept_language=self.headers["Accept-Language"],
        )
        # V23.62.60: N11 detail Session artik process-wide tutulur; burada
        # instance-owned HTTP pool yoktur. Force'lar arasi reuse module helper ile
        # saglanir. Timeout/identity/security/price kurallari degismez.

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

    @staticmethod
    def _security_page(html: str) -> bool:
        lowered = str(html or "").lower()
        markers = (
            "captcha", "access denied", "bot detection", "verify you are human",
            "güvenlik doğrulaması", "robot olmadığınızı", "akamai", "perimeterx",
            "attention required", "cloudflare",
        )
        return any(marker in lowered for marker in markers)

    def _strong_product_evidence(self, html: str) -> bool:
        """Gerçek ürün HTML'i güvenlik script kelimeleri içerirse false-positive'i önler."""
        raw = str(html or "")
        if len(raw) < 25_000:
            return False
        lowered = raw.casefold()
        json_product = (
            '"@type":"product"' in lowered
            or '"@type": "product"' in lowered
            or "'@type':'product'" in lowered
        )
        product_price = (
            "product:price:amount" in lowered
            or 'itemprop="price"' in lowered
            or 'property="og:price:amount"' in lowered
        )
        has_title = (
            "<h1" in lowered
            or 'property="og:title"' in lowered
            or "<title" in lowered
        )
        # MediaMarkt/Vatan gibi sayfalarda JSON-LD bazen client-side değişebilir;
        # konfigüre edilmiş gerçek ürün başlık + fiyat seçicileri ikinci kanıttır.
        selector_evidence = False
        try:
            tree = HTMLParser(raw)
            has_config_title = any(tree.css_first(sel) for sel in self.config.title_selectors)
            has_config_price = any(tree.css_first(sel) for sel in self.config.price_selectors)
            selector_evidence = bool(has_config_title and has_config_price)
        except Exception:
            selector_evidence = False
        return bool(json_product or (has_title and product_price) or selector_evidence)

    def _blocking_security_page(self, html: str) -> bool:
        if not self._security_page(html):
            return False
        if self._strong_product_evidence(html):
            print(
                f"V22.2 challenge classifier [{self.config.name}]: "
                "güvenlik kelimesi var ancak güçlü ürün kanıtı bulundu; ürün HTML'i kabul edildi."
            )
            return False
        return True

    def _download(self, url: str) -> str:
        # V23.62.39: N11 search varyansı kontrol altına alındıktan sonra kalan
        # detail HTTP varyansı 2-6 sn bandında gözlendi. Tek denemeli HTTP
        # yolunu 4.5 sn soft-cap ile sınırla; timeout/sağlıksız HTML durumunda
        # güvenlik ve güçlü ürün kanıtı kapıları korunarak hafif browser fallback'e geç.
        if self.config.code == "n11":
            retry = Retry(
                total=0,
                connect=0,
                read=0,
                status=0,
                backoff_factor=0.0,
                allowed_methods=frozenset({"GET", "HEAD"}),
                raise_on_status=False,
            )
            request_timeout_v23627 = 4.5
        else:
            retry = Retry(
                total=3,
                connect=3,
                read=3,
                status=3,
                backoff_factor=0.8,
                status_forcelist=(403, 408, 425, 429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET", "HEAD"}),
                raise_on_status=False,
            )
            request_timeout_v23627 = 35

        if self.config.code == "n11":
            session, request_index_v236260, n11_reused_session_v236260 = (
                _n11_shared_detail_session_v236260(retry)
            )
            print(
                "V23.62.60 N11 DETAIL HTTP CONNECTION: "
                f"request_index={request_index_v236260} "
                f"session_reused={n11_reused_session_v236260} "
                "scope=process keep_alive=True"
            )
        else:
            session = requests.Session()
            session.mount(
                "https://",
                HTTPAdapter(
                    max_retries=retry,
                    pool_connections=10,
                    pool_maxsize=10,
                    pool_block=False,
                ),
            )
        headers = dict(self.headers)
        headers.update({
            # Requests header değerleri latin-1 ile kodlanır. Mağaza adındaki
            # Türkçe karakterler doğrudan yazılırsa UnicodeEncodeError oluşur.
            "Referer": (
                "https://www.google.com/search?q="
                + quote_plus(self.config.name, safe="")
            ),
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Upgrade-Insecure-Requests": "1",
        })
        request_started_v23627 = perf_counter()
        try:
            response = session.get(
                url,
                headers=headers,
                timeout=request_timeout_v23627,
                allow_redirects=True,
            )
            html = response.text or ""
            request_elapsed_v23627 = perf_counter() - request_started_v23627
            print(
                f"V23.62.7 DETAIL HTTP [{self.config.name}]: "
                f"http={response.status_code} html={len(html)} "
                f"elapsed={request_elapsed_v23627:.3f}s "
                f"budget={request_timeout_v23627}s"
            )
            if response.ok and len(html) >= 5000 and not self._blocking_security_page(html):
                return html
        except requests.RequestException as error:
            request_elapsed_v23627 = perf_counter() - request_started_v23627
            print(
                f"V23.62.7 DETAIL HTTP FALLBACK [{self.config.name}]: "
                f"{type(error).__name__} elapsed={request_elapsed_v23627:.3f}s "
                f"budget={request_timeout_v23627}s"
            )
        finally:
            # V23.62.60: N11 process-wide persistent pool açık kalır; diğer mağazaların
            # önceki request-lifetime session davranışı korunur.
            if self.config.code != "n11":
                session.close()

        browser_error: Exception | None = None
        try:
            max_attempts = 1 if self.config.code in {"n11", "pazarama"} else 2
            for attempt in range(1, max_attempts + 1):
                try:
                    browser_started_v23627 = perf_counter()
                    n11_detail_fast_fallback_v236239 = self.config.code == "n11"
                    if n11_detail_fast_fallback_v236239:
                        print(
                            "V23.62.46 N11 DETAIL BROWSER CHALLENGE FAIL-FAST: "
                            "initial_wait=1.0s nav=12000ms scroll=False "
                            "challenge_recheck=0.5s strong-evidence-required"
                        )
                    result = self.browser_engine.download(
                        url,
                        security_detector=self._blocking_security_page,
                        initial_wait_seconds=(
                            1.0 if n11_detail_fast_fallback_v236239
                            else (7.0 if self.config.code == "mediamarkt" else 4.0)
                        ),
                        navigation_timeout_ms=(
                            12_000 if n11_detail_fast_fallback_v236239 else 90_000
                        ),
                        scroll_page=(not n11_detail_fast_fallback_v236239),
                        verification_title=(
                            f"{self.config.name} GÜVENLİK DOĞRULAMASI"
                        ),
                        verification_message=(
                            f"{self.config.name} güvenlik sayfası açtı. "
                            "Chrome penceresindeki doğrulamayı tamamlayıp "
                            "terminale dönün."
                        ),
                        verification_wait_seconds=(
                            0.5 if n11_detail_fast_fallback_v236239
                            else (3.0 if self.config.code == "pazarama" else None)
                        ),
                    )
                    browser_elapsed_v23627 = perf_counter() - browser_started_v23627
                    print(
                        f"V23.62.7 DETAIL BROWSER [{self.config.name}]: "
                        f"html={len(result.html or '')} "
                        f"elapsed={browser_elapsed_v23627:.3f}s"
                    )
                    if (
                        result.html
                        and len(result.html) >= 3000
                        and not self._blocking_security_page(result.html)
                    ):
                        return result.html
                    if (
                        self.config.code in {"n11", "pazarama"}
                        and self._blocking_security_page(result.html or "")
                    ):
                        raise RuntimeError(
                            "SECURITY_CHALLENGE: "
                            f"{self.config.name} güvenlik doğrulaması devam ediyor; "
                            "ürün HTML'i scraper pipeline'ına gönderilmedi."
                        )
                except Exception as error:
                    browser_error = error
                    print(
                        f"{self.config.name} Playwright deneme "
                        f"{attempt}/{max_attempts} hatası:",
                        type(error).__name__,
                        error,
                    )
                    if attempt == 1 and self._temporary_browser_profile:
                        shutil.rmtree(
                            self.browser_engine.profile_directory,
                            ignore_errors=True,
                        )
        finally:
            if self._temporary_browser_profile:
                shutil.rmtree(
                    self.browser_engine.profile_directory,
                    ignore_errors=True,
                )

        if browser_error is not None:
            raise RuntimeError(
                f"{self.config.name} ürün sayfası indirilemedi: "
                f"{type(browser_error).__name__}: {browser_error}"
            ) from browser_error
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

    @staticmethod
    def _clean_spec_pair(name: object, value: object) -> tuple[str, str] | None:
        key = " ".join(str(name or "").split()).strip(" :")
        val = " ".join(str(value or "").split()).strip()
        if not key or not val or len(key) > 120 or len(val) > 500:
            return None
        if key.casefold() == val.casefold():
            return None
        return key, val

    @classmethod
    def _extract_specifications(cls, tree: HTMLParser, product_node: dict[str, Any]) -> dict[str, str] | None:
        output: dict[str, str] = {}
        additional = product_node.get("additionalProperty") or product_node.get("additionalProperties") or []
        if isinstance(additional, dict):
            additional = [additional]
        if isinstance(additional, list):
            for item in additional:
                if not isinstance(item, dict):
                    continue
                pair = cls._clean_spec_pair(item.get("name") or item.get("propertyID"), item.get("value"))
                if pair:
                    output.setdefault(*pair)

        selectors = (
            "table tr", "[data-test*='specification'] li", "[data-testid*='specification'] li",
            "[class*='specification'] li", "[class*='technical'] li", ".specifications li",
            ".product-features li", ".product-detail-specification li",
        )
        for selector in selectors:
            for row in tree.css(selector)[:250]:
                cells = row.css("th,td")
                pair = None
                if len(cells) >= 2:
                    pair = cls._clean_spec_pair(cells[0].text(strip=True), cells[-1].text(strip=True))
                else:
                    text = " ".join(row.text(strip=True).split())
                    if ":" in text:
                        pair = cls._clean_spec_pair(*text.split(":", 1))
                if pair:
                    output.setdefault(*pair)
        return output or None

    @staticmethod
    def _first_matching_text(
        tree: HTMLParser,
        selectors: tuple[str, ...],
        keywords: tuple[str, ...] = (),
    ) -> str | None:
        for selector in selectors:
            for node in tree.css(selector)[:80]:
                value = " ".join(node.text(strip=True).split())
                if not value:
                    continue
                normalized = value.casefold()
                if not keywords or any(keyword in normalized for keyword in keywords):
                    return value[:180]
        return None

    @classmethod
    def _offer_detail_values(
        cls,
        tree: HTMLParser,
        product_node: dict[str, Any],
        offer: dict[str, Any],
        seller: str,
        store_name: str,
    ) -> dict[str, Any]:
        shipping_price = None
        shipping_method = None
        delivery_text = None
        warranty_type = None
        campaign_text = None
        installment_text = None

        shipping = offer.get("shippingDetails") or offer.get("shipping") or {}
        if isinstance(shipping, list):
            shipping = next((item for item in shipping if isinstance(item, dict)), {})
        if isinstance(shipping, dict):
            rate = shipping.get("shippingRate") or {}
            if isinstance(rate, dict):
                shipping_price = BaseParser._parse_price(
                    rate.get("value") or rate.get("price")
                )
                currency = rate.get("currency")
            else:
                shipping_price = BaseParser._parse_price(rate)
                currency = None

            delivery = shipping.get("deliveryTime") or {}
            if isinstance(delivery, dict):
                handling = delivery.get("handlingTime") or {}
                transit = delivery.get("transitTime") or {}
                candidates = []
                for item in (handling, transit):
                    if isinstance(item, dict):
                        minimum = item.get("minValue")
                        maximum = item.get("maxValue")
                        unit = item.get("unitCode") or item.get("unitText") or "gün"
                        if minimum is not None and maximum is not None:
                            candidates.append(f"{minimum}-{maximum} {unit}")
                delivery_text = ", ".join(candidates) or None
        else:
            currency = None

        shipping_text = cls._first_matching_text(
            tree,
            (
                "[class*='shipping']", "[data-test*='shipping']",
                "[data-testid*='shipping']", "[class*='cargo']",
                "[class*='kargo']",
            ),
            ("kargo", "teslim", "shipping"),
        )
        if shipping_text:
            normalized_shipping = shipping_text.casefold()
            if any(term in normalized_shipping for term in ("ücretsiz", "bedava", "free")):
                shipping_price = 0.0
                shipping_method = "Ücretsiz kargo"
            elif shipping_method is None:
                shipping_method = shipping_text[:100]

        delivery_text = delivery_text or cls._first_matching_text(
            tree,
            (
                "[class*='delivery']", "[data-test*='delivery']",
                "[data-testid*='delivery']", "[class*='shipment']",
            ),
            ("teslim", "kargo", "gün", "yarın", "bugün"),
        )
        warranty_type = cls._first_matching_text(
            tree,
            (
                "[class*='warranty']", "[data-test*='warranty']",
                "[data-testid*='warranty']", "[class*='garanti']",
            ),
            ("garanti", "warranty"),
        )
        campaign_text = cls._first_matching_text(
            tree,
            (
                "[class*='campaign']", "[class*='coupon']",
                "[data-test*='campaign']", "[data-testid*='campaign']",
                "[class*='discount']",
            ),
            ("kampanya", "indirim", "kupon", "sepette"),
        )
        installment_text = cls._first_matching_text(
            tree,
            (
                "[class*='installment']", "[data-test*='installment']",
                "[data-testid*='installment']", "[class*='taksit']",
            ),
            ("taksit", "installment"),
        )

        normalized_seller = " ".join(str(seller or "").casefold().split())
        normalized_store = " ".join(str(store_name or "").casefold().split())
        official = bool(
            normalized_seller
            and normalized_store
            and (
                normalized_seller == normalized_store
                or normalized_store in normalized_seller
            )
        )

        page_text = " ".join(tree.body.text(strip=True).split()) if tree.body else ""
        lower_page = page_text.casefold()
        sponsored = any(term in lower_page for term in ("sponsorlu", "reklam", "promoted"))

        return {
            "shipping_price": shipping_price,
            "shipping_method": shipping_method,
            "delivery_text": delivery_text,
            "warranty_type": warranty_type,
            "campaign_text": campaign_text,
            "installment_text": installment_text,
            "currency": str(offer.get("priceCurrency") or currency or "TRY"),
            "is_sponsored": sponsored,
            "is_official_seller": official,
        }

    def _verified_price_fallback_v236328(
        self, *, url: str, html: str, tree, product_node: dict, offer: dict
    ):
        """V23.63.28 opt-in hook; default is fail-closed/no fallback."""
        return None

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
            fallback_price_v236328 = self._verified_price_fallback_v236328(
                url=normalized_url, html=html, tree=tree, product_node=product_node, offer=offer
            )
            if fallback_price_v236328:
                price = BaseParser._parse_price(fallback_price_v236328)
        if not price:
            raise ValueError(f"{self.config.name} güncel fiyatı bulunamadı.")

        offer_details = self._offer_detail_values(
            tree=tree,
            product_node=product_node,
            offer=offer,
            seller=seller,
            store_name=self.config.name,
        )

        product = Product(
            name=name,
            price=price,
            old_price=old_price,
            rating=rating,
            review_count=review_count,
            seller=seller,
            url=normalized_url,
            image=image,
            image_gallery=serialize_image_gallery(
                collect_image_urls(html, primary=image, base_url=url)
            ),
            brand=self._brand(product_node),
            model=BaseParser._clean_text(product_node.get("model")),
            category=BaseParser._clean_text(product_node.get("category")),
            description=BaseParser._clean_description(product_node.get("description")),
            specifications=self._extract_specifications(tree, product_node),
            stock_status=stock,
            source_site=self.config.name,
            product_code=product_code,
            shipping_price=offer_details["shipping_price"],
            shipping_method=offer_details["shipping_method"],
            delivery_text=offer_details["delivery_text"],
            warranty_type=offer_details["warranty_type"],
            campaign_text=offer_details["campaign_text"],
            installment_text=offer_details["installment_text"],
            currency=offer_details["currency"],
            is_sponsored=offer_details["is_sponsored"],
            is_official_seller=offer_details["is_official_seller"],
        )
        return ProductIdentityService.enrich_product(product)
