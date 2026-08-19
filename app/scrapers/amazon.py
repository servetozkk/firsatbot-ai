from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlsplit, urlunsplit

import re
import time
import requests
from selectolax.parser import HTMLParser

from app.parsers.amazon_parser import AmazonParser
from app.scrapers.base import BaseScraper
from app.services.browser_engine import BrowserEngine


class AmazonScraper(BaseScraper):
    """
    Amazon Türkiye ürün sayfalarını indirir ve
    AmazonParser ile Product modeline dönüştürür.

    Önce requests yöntemi denenir. Amazon güvenlik,
    robot kontrolü veya eksik HTML döndürürse ortak
    BrowserEngine üzerinden kalıcı profilli Chrome
    kullanılır.
    """

    BASE_URL = "https://www.amazon.com.tr"

    SECURITY_TEXTS = (
        "robot check",
        "enter the characters you see below",
        "type the characters you see in this image",
        "sorry, we just need to make sure you're not a robot",
        "üzgünüz, yalnızca bir robot olmadığınızdan emin olmamız gerekiyor",
        "karakterleri aşağıdaki resimde gördüğünüz gibi girin",
        "captcha",
        "api-services-support@amazon.com",
        "/errors/validatecaptcha",
    )

    INVALID_PAGE_TEXTS = (
        "aradığınız sayfayı bulamadık",
        "sorry! we couldn't find that page",
        "the web address you entered is not a functioning page",
        "köpeklerimiz bu sayfayı bulamadı",
    )

    PRODUCT_MARKERS = (
        'id="productTitle"',
        "id='productTitle'",
        'id="dp"',
        "id='dp'",
        'name="ASIN"',
        "name='ASIN'",
        'data-feature-name="title"',
        "data-feature-name='title'",
    )

    def __init__(self) -> None:
        super().__init__("Amazon Türkiye")

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": (
                "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
            ),
            "Accept-Encoding": (
                "gzip, deflate, br"
            ),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        project_root = Path(
            __file__
        ).resolve().parents[2]

        self.profile_directory = (
            project_root
            / ".playwright-amazon-profile"
        )

        self.debug_file = (
            project_root
            / "amazon_debug.html"
        )

        self.browser_engine = BrowserEngine(
            profile_directory=(
                self.profile_directory
            ),
            locale="tr-TR",
            headless=False,
            channel="chrome",
            viewport_width=1440,
            viewport_height=1000,
            accept_language=self.headers[
                "Accept-Language"
            ],
        )

    @staticmethod
    def clean_product_url(
        url: str,
    ) -> str:
        """
        Amazon ürün bağlantısını doğrular ve takip
        parametrelerini kaldırır.

        Desteklenen temel yollar:

        /dp/ASIN
        /gp/product/ASIN
        /product/ASIN
        """

        normalized_url = str(
            url or ""
        ).strip()

        if not normalized_url:
            raise ValueError(
                "Amazon ürün bağlantısı boş."
            )

        if not normalized_url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            normalized_url = (
                f"https://{normalized_url}"
            )

        parts = urlsplit(
            normalized_url
        )

        hostname = (
            parts.hostname or ""
        ).lower()

        if not (
            hostname == "amazon.com.tr"
            or hostname.endswith(
                ".amazon.com.tr"
            )
        ):
            raise ValueError(
                "Bağlantı Amazon Türkiye alan "
                "adına ait değil."
            )

        clean_path = (
            AmazonScraper._clean_product_path(
                parts.path
            )
        )

        return urlunsplit(
            (
                "https",
                "www.amazon.com.tr",
                clean_path,
                "",
                "",
            )
        )

    @staticmethod
    def _clean_product_path(
        path: str,
    ) -> str:
        """
        Amazon URL yolunu mümkünse standart
        /dp/ASIN biçimine dönüştürür.
        """

        normalized_path = str(
            path or ""
        ).strip()

        if not normalized_path:
            raise ValueError(
                "Amazon ürün bağlantısında ürün yolu "
                "bulunamadı."
            )

        path_parts = [
            part
            for part in normalized_path.split("/")
            if part
        ]

        asin: str | None = None

        for index, part in enumerate(
            path_parts
        ):
            lowered_part = part.lower()

            if (
                lowered_part == "dp"
                and index + 1 < len(path_parts)
            ):
                asin = path_parts[
                    index + 1
                ]

                break

            if (
                lowered_part == "product"
                and index + 1 < len(path_parts)
            ):
                asin = path_parts[
                    index + 1
                ]

                break

        if asin:
            asin = asin.strip().upper()

            if (
                len(asin) == 10
                and asin.isalnum()
            ):
                return f"/dp/{asin}"

        return normalized_path

    @staticmethod
    def _extract_asin_from_url(url: str) -> str | None:
        match = re.search(
            r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)",
            str(url or ""),
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        asin = match.group(1).upper()
        return asin if len(asin) == 10 and asin.isalnum() else None

    def _recover_exact_asin_search_price(
        self,
        *,
        asin: str,
        timeout_seconds: float = 20.0,
    ) -> float | None:
        """V22.8: Detail sayfasında offer yoksa exact-ASIN search card fiyatı.

        Güvenlik:
        - Arama yalnız ASIN ile yapılır.
        - Yalnız data-asin veya href içinde TAM AYNI ASIN olan kart kabul edilir.
        - Taksit/eski fiyat sınıfları kullanılmaz.
        - Search card fiyatı detail ürün verisiyle birleşmeden tek başına Product üretmez.
        """
        asin = str(asin or "").strip().upper()
        if len(asin) != 10 or not asin.isalnum():
            return None

        search_url = (
            "https://www.amazon.com.tr/s?k="
            + quote_plus(asin)
        )

        try:
            session = requests.Session()
            session.headers.update(self.headers)
            response = session.get(
                search_url,
                timeout=max(0.5, float(timeout_seconds)),
                allow_redirects=True,
            )
            response.raise_for_status()
            response.encoding = (
                response.apparent_encoding
                or response.encoding
                or "utf-8"
            )
            html = response.text
        except Exception as error:
            print(
                "V22.8 Amazon exact-ASIN fiyat araması başarısız:",
                f"{type(error).__name__}: {error}",
            )
            return None

        if self._is_security_page(html) or len(html) < 3000:
            return None

        tree = HTMLParser(html)

        cards = list(
            tree.css(
                f'[data-asin="{asin}"],'
                f'[data-asin="{asin.lower()}"]'
            )
        )

        # data-asin yoksa exact href üzerinden en yakın result card'ı bul.
        if not cards:
            for link in tree.css("a[href]"):
                href = str(link.attributes.get("href") or "")
                if re.search(
                    rf"/(?:dp|gp/product)/{re.escape(asin)}(?:[/?]|$)",
                    href,
                    flags=re.IGNORECASE,
                ):
                    node = link
                    while node is not None:
                        attrs = getattr(node, "attributes", {}) or {}
                        classes = str(attrs.get("class") or "")
                        data_asin = str(attrs.get("data-asin") or "").upper()
                        if (
                            data_asin == asin
                            or "s-result-item" in classes
                        ):
                            cards.append(node)
                            break
                        node = getattr(node, "parent", None)
                    if cards:
                        break

        def parse_price_text(value: str | None) -> float | None:
            text = str(value or "").strip()
            if not text:
                return None
            # 2.399,00 TL / 2399,00 TL / 2.399 TL
            match = re.search(
                r"(?<!\d)(\d{1,3}(?:\.\d{3})+(?:,\d{2})?|\d{2,6}(?:,\d{2})?)\s*(?:TL|₺)?",
                text,
                flags=re.IGNORECASE,
            )
            if not match:
                return None
            raw = match.group(1)
            if "," in raw:
                integer, decimal = raw.rsplit(",", 1)
                normalized = integer.replace(".", "") + "." + decimal
            elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                normalized = raw.replace(".", "")
            else:
                normalized = raw
            try:
                value_num = float(normalized)
            except ValueError:
                return None
            return value_num if value_num > 0 else None

        for card in cards:
            card_asin = str(
                (getattr(card, "attributes", {}) or {}).get("data-asin") or ""
            ).upper()
            if card_asin and card_asin != asin:
                continue

            # Exact ASIN'i kart içindeki href ile de doğrula.
            exact_link = False
            for link in card.css("a[href]"):
                href = str(link.attributes.get("href") or "")
                if re.search(
                    rf"/(?:dp|gp/product)/{re.escape(asin)}(?:[/?]|$)",
                    href,
                    flags=re.IGNORECASE,
                ):
                    exact_link = True
                    break
            if not exact_link and card_asin != asin:
                continue

            selectors = (
                ".a-price:not(.a-text-price) .a-offscreen",
                ".a-price[data-a-color='base'] .a-offscreen",
                ".a-price .a-offscreen",
            )
            for selector in selectors:
                for node in card.css(selector):
                    price = parse_price_text(
                        node.text(separator=" ", strip=True)
                    )
                    if price is not None:
                        print(
                            "V22.8 Amazon exact-ASIN search card fiyatı:",
                            asin,
                            f"{price:.2f} TL",
                        )
                        return price

            # Offscreen yoksa whole+fraction fallback.
            whole = card.css_first(".a-price-whole")
            fraction = card.css_first(".a-price-fraction")
            if whole is not None:
                whole_text = whole.text(separator=" ", strip=True)
                fraction_text = (
                    fraction.text(separator=" ", strip=True)
                    if fraction is not None
                    else "00"
                )
                whole_digits = re.sub(r"[^\d]", "", whole_text)
                fraction_digits = re.sub(r"[^\d]", "", fraction_text)[:2]
                if whole_digits:
                    price = float(
                        f"{whole_digits}.{fraction_digits or '00'}"
                    )
                    if price > 0:
                        print(
                            "V22.8 Amazon exact-ASIN search card fiyatı:",
                            asin,
                            f"{price:.2f} TL",
                        )
                        return price

        print(
            "V22.8 Amazon exact-ASIN search card fiyatı bulunamadı:",
            asin,
        )
        return None

    def _recover_target_asin_offer_listing_price(
        self,
        *,
        asin: str,
        detail_html: str,
        timeout_seconds: float = 20.0,
    ) -> float | None:
        """V22.9: Hedef ASIN'in Amazon offer-listing sayfasından fiyat çözer.

        Detail sayfasında Buy Box fiyatı boş olup "Satın Alma Seçeneklerini Gör"
        bağlantısı bulunabilir. Bu yöntem yalnız detail HTML içindeki TAM AYNI ASIN
        offer-listing linkini takip eder; sponsorlu/recommended ürün fiyatlarını
        hiçbir zaman kullanmaz.
        """
        asin = str(asin or "").strip().upper()
        if len(asin) != 10 or not asin.isalnum():
            return None

        tree = HTMLParser(str(detail_html or ""))
        listing_url: str | None = None
        for link in tree.css("a[href]"):
            href = str(link.attributes.get("href") or "")
            if re.search(
                rf"/gp/offer-listing/{re.escape(asin)}(?:[/?]|$)",
                href,
                flags=re.IGNORECASE,
            ):
                listing_url = urljoin(self.BASE_URL, href)
                break

        if not listing_url:
            return None

        try:
            session = requests.Session()
            session.headers.update(self.headers)
            response = session.get(
                listing_url,
                timeout=max(0.5, float(timeout_seconds)),
                allow_redirects=True,
            )
            response.raise_for_status()
            response.encoding = (
                response.apparent_encoding
                or response.encoding
                or "utf-8"
            )
            html = response.text
        except Exception as error:
            print(
                "V22.9 Amazon offer-listing isteği başarısız:",
                f"{type(error).__name__}: {error}",
            )
            return None

        if self._is_security_page(html) or len(html) < 1500:
            return None

        # Hedef ASIN sayfası olduğuna dair açık kanıt gerekir.
        normalized = str(html or "")
        if asin not in normalized.upper():
            return None

        listing_tree = HTMLParser(html)
        selectors = (
            "#aod-offer .a-price:not(.a-text-price) .a-offscreen",
            "#aod-offer .a-price .a-offscreen",
            ".aod-offer .a-price:not(.a-text-price) .a-offscreen",
            ".olpOffer .olpOfferPrice",
            ".olpOfferPrice",
            "#olpOfferList .a-price:not(.a-text-price) .a-offscreen",
        )

        def parse_price(value: str | None) -> float | None:
            text = str(value or "").strip()
            match = re.search(
                r"(?<!\d)(\d{1,3}(?:\.\d{3})+(?:,\d{2})?|\d{2,6}(?:,\d{2})?)\s*(?:TL|₺)?",
                text,
                flags=re.IGNORECASE,
            )
            if not match:
                return None
            raw = match.group(1)
            if "," in raw:
                integer, decimal = raw.rsplit(",", 1)
                normalized_price = integer.replace(".", "") + "." + decimal
            elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw):
                normalized_price = raw.replace(".", "")
            else:
                normalized_price = raw
            try:
                result = float(normalized_price)
            except ValueError:
                return None
            return result if result > 0 else None

        prices: list[float] = []
        for selector in selectors:
            for node in listing_tree.css(selector):
                text = node.text(separator=" ", strip=True)
                price = parse_price(text)
                if price is not None:
                    prices.append(price)

        if not prices:
            return None

        winner = min(prices)
        print(
            "V22.9 Amazon target-ASIN offer-listing fiyatı:",
            asin,
            f"{winner:.2f} TL",
        )
        return winner

    @staticmethod
    def _looks_like_no_buyable_offer(
        *,
        html: str,
        asin: str | None,
    ) -> bool:
        """Detail HTML hedef ürünü gösteriyor ama doğrudan satın alınabilir fiyat yok."""
        text = str(html or "")
        folded = text.casefold()
        asin = str(asin or "").upper()
        exact_asin = bool(asin and asin in text.upper())
        has_empty_core_price = bool(
            re.search(
                r'''id=["\']corePrice_desktop["\'][^>]*>\s*<div[^>]*>\s*</div>''',
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
        )
        has_offer_listing = bool(
            asin
            and re.search(
                rf"/gp/offer-listing/{re.escape(asin)}(?:[/?]|$)",
                text,
                flags=re.IGNORECASE,
            )
        )
        has_unqualified_buybox = 'id="unqualifiedBuyBox"' in text or "id='unqualifiedBuyBox'" in text
        aod_no_offers = bool(
            re.search(
                r'''id=["\']aod-has-oas-offers["\'][^>]*value=["\']false["\']''',
                text,
                flags=re.IGNORECASE,
            )
        )
        unavailable = (
            "şu anda mevcut değil" in folded
            or "currently unavailable" in folded
        )
        return exact_asin and (
            (has_empty_core_price and has_offer_listing)
            or (has_unqualified_buybox and aod_no_offers)
            or (has_empty_core_price and unavailable)
        )

    def scrape(
        self,
        url: str,
    ):
        """
        Tek bir Amazon Türkiye ürün sayfasını okur.

        Önce requests kullanılır. Requests güvenlik
        sayfası, eksik sayfa veya parse hatası üretirse
        BrowserEngine ile Chrome üzerinden tekrar
        denenir.
        """

        clean_url = self.clean_product_url(
            url
        )

        print()
        print("=" * 70)
        print("AMAZON SCRAPER")
        print("=" * 70)
        print("Amazon ürünü açılıyor:")
        print(clean_url)

        requests_error: Exception | None = None
        asin = self._extract_asin_from_url(clean_url)
        requests_html: str | None = None

        # V23.62.72: one wall-clock budget for the complete Amazon detail chain.
        # Previous versions bounded each transport independently, allowing
        # detail + offer-listing + exact-ASIN search + browser to accumulate.
        detail_budget_seconds = 18.0
        detail_deadline = time.monotonic() + detail_budget_seconds

        def remaining_budget(*, cap: float | None = None) -> float:
            remaining = max(0.0, detail_deadline - time.monotonic())
            if cap is not None:
                remaining = min(remaining, float(cap))
            return remaining

        try:
            initial_timeout = remaining_budget(cap=6.0)
            if initial_timeout < 0.5:
                raise TimeoutError("V23.62.72 Amazon detail total budget exhausted before HTTP detail")
            requests_html = self._download_with_requests(
                clean_url,
                timeout_seconds=initial_timeout,
            )

            product = self._parse_product(
                html=requests_html,
                url=clean_url,
            )

            print(
                "Amazon ürünü requests ile "
                "başarıyla okundu."
            )

            return product

        except Exception as error:
            requests_error = error

            print(
                "Requests yöntemi başarısız:",
                type(error).__name__,
                error,
            )

            # Detail sayfası gerçek hedef ürünü gösteriyor ancak fiyat yoksa,
            # önce TAM AYNI ASIN'in Amazon offer-listing sayfasını çöz.
            if (
                asin
                and requests_html
                and "Amazon ürün fiyatı bulunamadı" in str(error)
            ):
                recovery_timeout = remaining_budget(cap=4.0)
                fallback_price = None
                if recovery_timeout >= 0.5:
                    fallback_price = self._recover_target_asin_offer_listing_price(
                        asin=asin,
                        detail_html=requests_html,
                        timeout_seconds=recovery_timeout,
                    )
                if fallback_price is None:
                    recovery_timeout = remaining_budget(cap=4.0)
                    if recovery_timeout >= 0.5:
                        fallback_price = self._recover_exact_asin_search_price(
                            asin=asin,
                            timeout_seconds=recovery_timeout,
                        )
                if fallback_price is not None:
                    try:
                        product = self._parse_product(
                            html=requests_html,
                            url=clean_url,
                            fallback_price=fallback_price,
                        )
                        print(
                            "Amazon ürünü requests + target-ASIN teklif fiyatı ile "
                            "başarıyla okundu."
                        )
                        return product
                    except Exception as fallback_error:
                        print(
                            "V22.9 requests target-ASIN fallback parse edilemedi:",
                            f"{type(fallback_error).__name__}: {fallback_error}",
                        )

            print(
                "Ortak BrowserEngine ile kalıcı "
                "profilli Chrome deneniyor..."
            )

        browser_html: str | None = None
        try:
            browser_remaining = remaining_budget(cap=6.0)
            if browser_remaining < 1.0:
                raise TimeoutError(
                    "V23.62.72 Amazon detail total budget exhausted before browser fallback"
                )
            browser_html = self._download_with_playwright(
                clean_url,
                navigation_timeout_ms=max(1_000, int(browser_remaining * 1000)),
            )

            product = self._parse_product(
                html=browser_html,
                url=clean_url,
            )

            print(
                "Amazon ürünü Chrome ile "
                "başarıyla okundu."
            )

            return product

        except Exception as playwright_error:
            if (
                asin
                and browser_html
                and "Amazon ürün fiyatı bulunamadı" in str(playwright_error)
            ):
                recovery_timeout = remaining_budget(cap=3.0)
                fallback_price = None
                if recovery_timeout >= 0.5:
                    fallback_price = self._recover_target_asin_offer_listing_price(
                        asin=asin,
                        detail_html=browser_html,
                        timeout_seconds=recovery_timeout,
                    )
                if fallback_price is None:
                    recovery_timeout = remaining_budget(cap=3.0)
                    if recovery_timeout >= 0.5:
                        fallback_price = self._recover_exact_asin_search_price(
                            asin=asin,
                            timeout_seconds=recovery_timeout,
                        )
                if fallback_price is not None:
                    try:
                        product = self._parse_product(
                            html=browser_html,
                            url=clean_url,
                            fallback_price=fallback_price,
                        )
                        print(
                            "Amazon ürünü Chrome + target-ASIN teklif fiyatı ile "
                            "başarıyla okundu."
                        )
                        return product
                    except Exception as fallback_error:
                        print(
                            "V22.9 Chrome target-ASIN fallback parse edilemedi:",
                            f"{type(fallback_error).__name__}: {fallback_error}",
                        )

                # Debug HTML'de gördüğümüz gerçek durum: hedef ASIN detail sayfası
                # mevcut, core price boş ve yalnız Satın Alma Seçenekleri ingress'i
                # var. Reklam/öneri fiyatı kullanmak yerine açık durum döndür.
                if self._looks_like_no_buyable_offer(
                    html=browser_html,
                    asin=asin,
                ):
                    detail_title_v236282 = self._extract_detail_title_v236282(browser_html)
                    print(
                        "V23.62.82 AMAZON NO-BUYABLE DETAIL IDENTITY EVIDENCE:",
                        f"asin={asin}",
                        f"title={detail_title_v236282 or 'UNKNOWN'}",
                    )
                    raise RuntimeError(
                        "NO_BUYABLE_OFFER: Amazon hedef ASIN için güvenilir "
                        "satın alınabilir teklif fiyatı sunmuyor. "
                        f"DETAIL_TITLE_V236282={detail_title_v236282}"
                    ) from playwright_error

            raise RuntimeError(
                "Amazon Türkiye ürünü okunamadı. "
                f"Requests hatası: {requests_error}. "
                "Chrome hatası: "
                f"{playwright_error}"
            ) from playwright_error

    def _download_with_requests(
        self,
        url: str,
        *,
        timeout_seconds: float = 8.0,
    ) -> str:
        """
        Ürün sayfasını requests ile indirir.
        """

        session = requests.Session()

        session.headers.update(
            self.headers
        )

        response = session.get(
            url,
            # V23.62.71: bounded Amazon detail HTTP budget for explicit force scans.
            # A single candidate must not consume ~30s before the already-bounded
            # browser fallback. Exact-ASIN recovery and fail-closed semantics remain.
            timeout=max(0.5, float(timeout_seconds)),
            allow_redirects=True,
        )

        print(
            "Requests HTTP:",
            response.status_code,
        )

        print(
            "Requests son URL:",
            response.url,
        )

        response.raise_for_status()

        response.encoding = (
            response.apparent_encoding
            or response.encoding
            or "utf-8"
        )

        html = response.text

        print(
            "Requests sayfa uzunluğu:",
            len(html),
        )

        if self._is_security_page(html):
            raise PermissionError(
                "Requests Amazon robot kontrolü "
                "veya CAPTCHA sayfasına yönlendirildi."
            )

        if self._is_invalid_page(html):
            raise ValueError(
                "Amazon ürün sayfası bulunamadı."
            )

        if len(html) < 3000:
            raise ValueError(
                "Requests ile alınan Amazon HTML "
                "içeriği beklenenden kısa."
            )

        if not self._looks_like_product_page(
            html
        ):
            raise ValueError(
                "Requests ile alınan sayfa bir Amazon "
                "ürün sayfasına benzemiyor."
            )

        return html

    def _download_with_playwright(
        self,
        url: str,
        *,
        navigation_timeout_ms: int = 8_000,
    ) -> str:
        """
        Ürün sayfasını ortak BrowserEngine üzerinden
        kalıcı profilli Chrome ile indirir.
        """

        result = self.browser_engine.download(
            url=url,
            security_detector=(
                self._is_security_page
            ),
            debug_file=self.debug_file,
            # V23.62.69: browser fallback is a bounded last resort.
            # Requests-first and exact-ASIN recovery remain authoritative;
            # a no-buyable-offer detail must not hold the whole parallel force
            # scan for ~60-80 seconds.
            initial_wait_seconds=1.0,
            navigation_timeout_ms=max(1_000, int(navigation_timeout_ms)),
            scroll_page=False,
            verification_title=(
                "AMAZON GÜVENLİK DOĞRULAMASI"
            ),
            verification_message=(
                "Chrome penceresinde Amazon robot "
                "kontrolü veya CAPTCHA görünüyorsa "
                "doğrulamayı tamamlayın."
            ),
        )

        html = result.html

        print(
            "Chrome sayfa uzunluğu:",
            len(html),
        )

        if self._is_security_page(html):
            raise PermissionError(
                "Güvenlik doğrulamasından sonra da "
                "Amazon robot kontrolü veya CAPTCHA "
                "sayfası gösteriliyor."
            )

        if self._is_invalid_page(html):
            raise ValueError(
                "Chrome ile açılan Amazon ürün sayfası "
                "bulunamadı."
            )

        if len(html) < 3000:
            raise ValueError(
                "Chrome ile alınan Amazon HTML "
                "içeriği beklenenden kısa."
            )

        if not self._looks_like_product_page(
            html
        ):
            raise ValueError(
                "Chrome ile alınan sayfa bir Amazon "
                "ürün sayfasına benzemiyor."
            )

        return html

    def _is_security_page(
        self,
        html: str,
    ) -> bool:
        """
        Amazon robot kontrolü, güvenlik veya CAPTCHA
        sayfası olup olmadığını belirler.
        """

        normalized_html = (
            self._normalize_lookup_text(
                html
            )
        )

        return any(
            self._normalize_lookup_text(
                security_text
            )
            in normalized_html
            for security_text in (
                self.SECURITY_TEXTS
            )
        )

    def _is_invalid_page(
        self,
        html: str,
    ) -> bool:
        """
        Amazon 404 veya bulunamadı sayfasını belirler.
        """

        normalized_html = (
            self._normalize_lookup_text(
                html
            )
        )

        return any(
            self._normalize_lookup_text(
                invalid_text
            )
            in normalized_html
            for invalid_text in (
                self.INVALID_PAGE_TEXTS
            )
        )

    def _looks_like_product_page(
        self,
        html: str,
    ) -> bool:
        """
        HTML içeriğinin Amazon ürün detay sayfasına
        benzeyip benzemediğini kontrol eder.
        """

        normalized_html = str(
            html or ""
        )

        if any(
            marker in normalized_html
            for marker in self.PRODUCT_MARKERS
        ):
            return True

        lowered_html = (
            normalized_html.lower()
        )

        fallback_markers = (
            '"@type":"product"',
            '"@type": "product"',
            "id=\"coreprice",
            "id='coreprice",
            "id=\"availability",
            "id='availability",
            "id=\"landingimage",
            "id='landingimage",
        )

        return any(
            marker in lowered_html
            for marker in fallback_markers
        )

    @staticmethod
    def _normalize_lookup_text(
        value: str,
    ) -> str:
        """
        Güvenlik metni karşılaştırmalarında kullanılmak
        üzere Türkçe karakterleri ve boşlukları
        normalleştirir.
        """

        text = str(
            value or ""
        ).lower()

        replacements = {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
        }

        for source, target in (
            replacements.items()
        ):
            text = text.replace(
                source,
                target,
            )

        return " ".join(
            text.split()
        )


    @staticmethod
    def _extract_detail_title_v236282(html: str | None) -> str:
        """Fail-closed identity evidence from the SAME Amazon detail HTML.

        Used only to decide whether a NO_BUYABLE first candidate is actually
        a different phone variant. It never supplies price and never accepts
        an offer.
        """
        if not html:
            return ""
        try:
            tree = HTMLParser(html)
            node = tree.css_first("#productTitle")
            if node is not None:
                text = " ".join(node.text(separator=" ").split())
                if text:
                    return text[:500]
            for selector in ('meta[property="og:title"]', 'meta[name="title"]'):
                node = tree.css_first(selector)
                if node is not None:
                    text = " ".join(str(node.attributes.get("content") or "").split())
                    if text:
                        return text[:500]
            node = tree.css_first("title")
            if node is not None:
                return " ".join(node.text(separator=" ").split())[:500]
        except Exception:
            return ""
        return ""

    @staticmethod
    def _parse_product(
        html: str,
        url: str,
        fallback_price: float | None = None,
    ):
        """
        Amazon HTML içeriğini AmazonParser ile
        Product modeline dönüştürür.
        """

        parser = AmazonParser()

        return parser.parse(
            html=html,
            url=url,
            fallback_price=fallback_price,
        )
