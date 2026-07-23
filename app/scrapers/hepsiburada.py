from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests
from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from app.parsers.hepsiburada_parser import (
    HepsiburadaParser,
)
from app.scrapers.base import BaseScraper


class HepsiburadaScraper(BaseScraper):
    BASE_URL = "https://www.hepsiburada.com"

    SECURITY_TEXTS = (
        "hepsiburada | güvenlik",
        "hepsiburada | security",
        "hbblockandcaptcha",
        "akreferanceid",
        "security/hbblockandcaptcha",
    )

    def __init__(self):
        super().__init__("Hepsiburada")

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": (
                "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
            ),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

        project_root = Path(__file__).resolve().parents[2]

        self.profile_directory = (
            project_root
            / ".playwright-hepsiburada-profile"
        )

        self.debug_file = (
            project_root
            / "hb_debug.html"
        )

    @staticmethod
    def clean_product_url(
        url: str,
    ) -> str:
        """
        Takip ve kampanya sorgu parametrelerini kaldırır.
        """

        url = str(url or "").strip()

        if not url:
            raise ValueError(
                "Hepsiburada ürün bağlantısı boş."
            )

        parts = urlsplit(url)

        if not parts.scheme:
            url = f"https://{url}"
            parts = urlsplit(url)

        hostname = (
            parts.hostname or ""
        ).lower()

        if not (
            hostname == "hepsiburada.com"
            or hostname.endswith(
                ".hepsiburada.com"
            )
        ):
            raise ValueError(
                "Bağlantı Hepsiburada alan adına ait değil."
            )

        return urlunsplit(
            (
                parts.scheme or "https",
                parts.netloc,
                parts.path,
                "",
                "",
            )
        )

    def scrape(
        self,
        url: str,
    ):
        """
        Tek bir Hepsiburada ürün sayfasını okur.

        Önce requests yöntemi denenir. Bu yöntem 403 veya güvenlik
        sayfası döndürürse kalıcı profilli gerçek Chrome açılır.
        """

        clean_url = self.clean_product_url(url)

        print("Hepsiburada ürünü açılıyor:")
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
                "Ürün requests ile başarıyla okundu."
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
                "Kalıcı profilli gerçek Chrome deneniyor..."
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
                "Ürün Chrome ile başarıyla okundu."
            )

            return product

        except Exception as playwright_error:
            raise RuntimeError(
                "Hepsiburada ürünü okunamadı. "
                f"Requests hatası: {requests_error}. "
                f"Chrome hatası: {playwright_error}"
            ) from playwright_error

    def _download_with_requests(
        self,
        url: str,
    ) -> str:
        response = requests.get(
            url,
            headers=self.headers,
            timeout=30,
            allow_redirects=True,
        )

        print(
            "Requests HTTP:",
            response.status_code,
        )

        response.raise_for_status()

        html = response.text

        print(
            "Requests sayfa uzunluğu:",
            len(html),
        )

        if self._is_security_page(html):
            raise PermissionError(
                "Requests güvenlik sayfasına yönlendirildi."
            )

        if len(html) < 1000:
            raise ValueError(
                "Requests ile alınan HTML çok kısa."
            )

        return html

    def _download_with_playwright(
        self,
        url: str,
    ) -> str:
        self.profile_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            "Chrome profil klasörü:"
        )
        print(
            self.profile_directory
        )

        with sync_playwright() as playwright:
            context = (
                playwright.chromium.launch_persistent_context(
                    user_data_dir=str(
                        self.profile_directory
                    ),
                    channel="chrome",
                    headless=False,
                    locale="tr-TR",
                    viewport={
                        "width": 1440,
                        "height": 1000,
                    },
                    extra_http_headers={
                        "Accept-Language": (
                            self.headers[
                                "Accept-Language"
                            ]
                        ),
                    },
                    args=[
                        "--start-maximized",
                    ],
                )
            )

            try:
                page = self._get_page(context)

                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                if response is not None:
                    print(
                        "Chrome HTTP:",
                        response.status,
                    )

                page.wait_for_timeout(5000)

                html = page.content()

                if self._is_security_page(html):
                    print()
                    print(
                        "=" * 70
                    )
                    print(
                        "HEPSİBURADA GÜVENLİK DOĞRULAMASI"
                    )
                    print(
                        "=" * 70
                    )
                    print(
                        "Chrome penceresinde güvenlik doğrulaması "
                        "veya CAPTCHA görünüyorsa tamamla."
                    )
                    print(
                        "Ürün sayfası tamamen açıldıktan sonra "
                        "bu PowerShell penceresine dön."
                    )
                    print()

                    input(
                        "Doğrulama tamamlanınca Enter'a bas: "
                    )

                    self._reload_after_verification(
                        page=page,
                        url=url,
                    )

                    html = page.content()

                self._scroll_product_page(page)

                html = page.content()

                print(
                    "Chrome sayfa başlığı:",
                    page.title(),
                )

                print(
                    "Chrome sayfa uzunluğu:",
                    len(html),
                )

                self._save_debug_html(html)

                if self._is_security_page(html):
                    raise PermissionError(
                        "Güvenlik doğrulamasından sonra da "
                        "Hepsiburada güvenlik sayfası gösteriliyor."
                    )

                if len(html) < 3000:
                    raise ValueError(
                        "Chrome ile alınan HTML beklenenden kısa."
                    )

                return html

            finally:
                context.close()

    @staticmethod
    def _get_page(
        context,
    ) -> Page:
        if context.pages:
            return context.pages[0]

        return context.new_page()

    def _reload_after_verification(
        self,
        page: Page,
        url: str,
    ) -> None:
        current_url = page.url.lower()

        if (
            "hepsiburada.com" not in current_url
            or "security" in current_url
        ):
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )
        else:
            try:
                page.reload(
                    wait_until="domcontentloaded",
                    timeout=60000,
                )
            except PlaywrightTimeoutError:
                print(
                    "Sayfa yenileme zaman aşımına uğradı; "
                    "mevcut sayfa kullanılacak."
                )

        page.wait_for_timeout(5000)

    @staticmethod
    def _scroll_product_page(
        page: Page,
    ) -> None:
        for _ in range(4):
            page.mouse.wheel(
                0,
                1200,
            )

            page.wait_for_timeout(
                750
            )

        page.mouse.wheel(
            0,
            -4800,
        )

        page.wait_for_timeout(
            1000
        )

    def _save_debug_html(
        self,
        html: str,
    ) -> None:
        self.debug_file.write_text(
            html,
            encoding="utf-8",
        )

        print(
            "Debug HTML oluşturuldu:"
        )
        print(
            self.debug_file
        )

    def _is_security_page(
        self,
        html: str,
    ) -> bool:
        normalized_html = (
            str(html or "")
            .lower()
            .replace("ü", "u")
            .replace("ı", "i")
            .replace("ş", "s")
            .replace("ğ", "g")
            .replace("ö", "o")
            .replace("ç", "c")
        )

        normalized_security_texts = (
            text
            .lower()
            .replace("ü", "u")
            .replace("ı", "i")
            .replace("ş", "s")
            .replace("ğ", "g")
            .replace("ö", "o")
            .replace("ç", "c")
            for text in self.SECURITY_TEXTS
        )

        return any(
            text in normalized_html
            for text in normalized_security_texts
        )

    @staticmethod
    def _parse_product(
        html: str,
        url: str,
    ):
        parser = HepsiburadaParser()

        return parser.parse(
            html=html,
            url=url,
        )