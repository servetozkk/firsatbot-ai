from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

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

        try:
            html = self._download_with_requests(
                clean_url
            )

            product = self._parse_product(
                html=html,
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
                "Amazon ürünü Chrome ile "
                "başarıyla okundu."
            )

            return product

        except Exception as playwright_error:
            raise RuntimeError(
                "Amazon Türkiye ürünü okunamadı. "
                f"Requests hatası: {requests_error}. "
                "Chrome hatası: "
                f"{playwright_error}"
            ) from playwright_error

    def _download_with_requests(
        self,
        url: str,
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
            initial_wait_seconds=6.0,
            navigation_timeout_ms=60_000,
            scroll_page=True,
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
    def _parse_product(
        html: str,
        url: str,
    ):
        """
        Amazon HTML içeriğini AmazonParser ile
        Product modeline dönüştürür.
        """

        parser = AmazonParser()

        return parser.parse(
            html=html,
            url=url,
        )
