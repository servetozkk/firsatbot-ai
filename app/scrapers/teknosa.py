from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

from app.parsers.teknosa_parser import TeknosaParser
from app.scrapers.base import BaseScraper
from app.services.browser_engine import BrowserEngine


class TeknosaScraper(BaseScraper):
    """
    Teknosa ürün sayfalarını indirir ve TeknosaParser ile
    Product modeline dönüştürür.

    Önce requests denenir. Eksik/dinamik HTML, güvenlik
    sayfası veya parse hatası alınırsa ortak BrowserEngine
    üzerinden kalıcı profilli Chrome kullanılır.
    """

    BASE_URL = "https://www.teknosa.com"

    SECURITY_TEXTS = (
        "<title>access denied",
        "<title>request blocked",
        "<title>security check",
        "/captcha/",
        "g-recaptcha",
        "hcaptcha",
        "robot olmadığınızı doğrulayın",
        "robot olmadiginizi dogrulayin",
        "olağandışı trafik algılandı",
        "olagandisi trafik algilandi",
    )

    INVALID_PAGE_TEXTS = (
        "<title>sayfa bulunamadı",
        "<title>sayfa bulunamadi",
        "aradığınız ürün bulunamadı",
        "aradiginiz urun bulunamadi",
        "bu ürün artık satışta değil",
        "bu urun artik satista degil",
    )

    PRODUCT_MARKERS = (
        '"@type":"product"',
        '"@type": "product"',
        "product:price:amount",
        'itemprop="price"',
        "sepete ekle",
        "ürün kodu",
        "teknik özellikler",
        "productdetail",
        "product-detail",
    )

    def __init__(self) -> None:
        super().__init__("Teknosa")

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
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.teknosa.com/",
            "Connection": "keep-alive",
        }

        project_root = Path(
            __file__
        ).resolve().parents[2]

        self.profile_directory = (
            project_root
            / ".playwright-teknosa-profile"
        )

        self.debug_file = (
            project_root
            / "teknosa_debug.html"
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
        Teknosa ürün bağlantısını doğrular ve reklam/takip
        parametrelerini kaldırır.
        """
        normalized_url = str(
            url or ""
        ).strip()

        if not normalized_url:
            raise ValueError(
                "Teknosa ürün bağlantısı boş."
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
            hostname == "teknosa.com"
            or hostname.endswith(
                ".teknosa.com"
            )
        ):
            raise ValueError(
                "Bağlantı Teknosa alan adına ait değil."
            )

        path = str(
            parts.path or ""
        ).strip()

        if (
            not path
            or path == "/"
            or "-p-" not in path.lower()
        ):
            raise ValueError(
                "Bağlantı geçerli bir Teknosa ürün "
                "sayfasına benzemiyor."
            )

        return urlunsplit(
            (
                "https",
                "www.teknosa.com",
                path,
                "",
                "",
            )
        )

    def scrape(
        self,
        url: str,
    ):
        clean_url = self.clean_product_url(
            url
        )

        print()
        print("=" * 70)
        print("TEKNOSA SCRAPER")
        print("=" * 70)
        print("Teknosa ürünü açılıyor:")
        print(clean_url)

        requests_error: Exception | None = None

        try:
            html = self._download_with_requests(
                clean_url
            )

            product = self._parse_product(
                html=html,
                url=clean_url,
            )

            print(
                "Teknosa ürünü requests ile "
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

            print(
                "Ortak BrowserEngine ile kalıcı "
                "profilli Chrome deneniyor..."
            )

        try:
            html = self._download_with_playwright(
                clean_url
            )

            product = self._parse_product(
                html=html,
                url=clean_url,
            )

            print(
                "Teknosa ürünü Chrome ile "
                "başarıyla okundu."
            )

            return product

        except Exception as playwright_error:
            import traceback

            print()
            print("TEKNOSA CHROME HATASI")
            print("-" * 70)
            traceback.print_exc()

            raise RuntimeError(
                "Teknosa ürünü okunamadı. "
                f"Requests hatası: "
                f"{type(requests_error).__name__ if requests_error else 'Yok'}: "
                f"{requests_error}. "
                "Chrome hatası: "
                f"{type(playwright_error).__name__}: "
                f"{playwright_error}"
            ) from playwright_error

    def _download_with_requests(
        self,
        url: str,
    ) -> str:
        session = requests.Session()
        session.headers.update(
            self.headers
        )

        response = session.get(
            url,
            timeout=30,
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

        self._validate_html(
            html
        )

        return html

    def _download_with_playwright(
        self,
        url: str,
    ) -> str:
        result = self.browser_engine.download(
            url=url,
            security_detector=(
                self._is_security_page
            ),
            debug_file=self.debug_file,
            initial_wait_seconds=8.0,
            navigation_timeout_ms=90_000,
            scroll_page=True,
            verification_title=(
                "TEKNOSA GÜVENLİK DOĞRULAMASI"
            ),
            verification_message=(
                "Chrome penceresinde Teknosa güvenlik "
                "kontrolü görünüyorsa doğrulamayı "
                "tamamlayın."
            ),
        )

        html = result.html

        print(
            "Chrome sayfa uzunluğu:",
            len(html),
        )

        self._validate_html(
            html
        )

        return html

    def _validate_html(
        self,
        html: str,
    ) -> None:
        html_text = str(html or "")
        html_length = len(html_text)

        if html_length < 800:
            raise ValueError(
                "Teknosa HTML içeriği boş veya çok kısa. "
                f"Uzunluk: {html_length}"
            )

        # Güvenlik ifadeleri büyük ürün HTML'lerinin JavaScript
        # dosyalarında da geçebilir. Bu nedenle yalnızca gerçekten
        # kısa/engelleme sayfasına benzeyen içeriklerde engel sayılır.
        if (
            html_length < 40_000
            and self._is_security_page(html_text)
        ):
            raise PermissionError(
                "Teknosa güvenlik veya CAPTCHA "
                "sayfası gösteriyor."
            )

        if (
            html_length < 40_000
            and self._is_invalid_page(html_text)
        ):
            raise ValueError(
                "Teknosa ürün sayfası bulunamadı."
            )

        if not self._looks_like_product_page(
            html_text
        ):
            debug_preview = " ".join(
                html_text[:500].split()
            )
            raise ValueError(
                "Alınan HTML bir Teknosa ürün sayfasına "
                "benzemiyor. "
                f"Uzunluk: {html_length}. "
                f"Başlangıç: {debug_preview}"
            )

    def _is_security_page(
        self,
        html: str,
    ) -> bool:
        normalized = self._normalize_lookup_text(
            html
        )

        return any(
            self._normalize_lookup_text(text)
            in normalized
            for text in self.SECURITY_TEXTS
        )

    def _is_invalid_page(
        self,
        html: str,
    ) -> bool:
        normalized = self._normalize_lookup_text(
            html
        )

        return any(
            self._normalize_lookup_text(text)
            in normalized
            for text in self.INVALID_PAGE_TEXTS
        )

    def _looks_like_product_page(
        self,
        html: str,
    ) -> bool:
        lowered = str(
            html or ""
        ).casefold()

        # URL'deki Teknosa ürün kodunun sayfa kaynaklarında bulunması
        # güçlü bir ürün sayfası işaretidir.
        has_product_code = (
            "-p-" in lowered
            and "100000" in lowered
        )

        has_json_product = (
            '"@type":"product"' in lowered
            or '"@type": "product"' in lowered
        )

        has_price = (
            "product:price:amount" in lowered
            or 'itemprop="price"' in lowered
            or '"price"' in lowered
        )

        has_title = (
            "<h1" in lowered
            or "og:title" in lowered
            or '"name"' in lowered
        )

        marker_count = sum(
            1
            for marker in self.PRODUCT_MARKERS
            if marker in lowered
        )

        return (
            has_json_product
            or (
                has_price
                and has_title
                and (
                    has_product_code
                    or marker_count >= 1
                )
            )
            or marker_count >= 2
        )

    @staticmethod
    def _normalize_lookup_text(
        value: str,
    ) -> str:
        text = str(
            value or ""
        ).casefold()

        replacements = {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
        }

        for source, target in replacements.items():
            text = text.replace(
                source,
                target,
            )

        return " ".join(
            text.split()
        )

    @staticmethod
    def _parse_product(
        html: str,
        url: str,
    ):
        parser = TeknosaParser()

        return parser.parse(
            html=html,
            url=url,
        )