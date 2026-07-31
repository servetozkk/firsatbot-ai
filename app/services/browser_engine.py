from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from playwright.sync_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


SecurityDetector = Callable[[str], bool]


@dataclass(slots=True)
class BrowserDownloadResult:
    html: str
    title: str
    final_url: str
    status_code: int | None


class BrowserEngine:
    """
    Playwright tabanlı ortak tarayıcı indirme motoru.

    Özellikler:
    - Kalıcı Chrome profili kullanır.
    - Açılan veya değişen sekmeleri yeniden tespit eder.
    - Kapanmış Page nesnesini tekrar kullanmaz.
    - CAPTCHA/güvenlik sayfasında kullanıcı doğrulamasını destekler.
    - Sayfa kaydırma ve debug HTML kaydetme işlemlerini yapar.
    """

    def __init__(
        self,
        profile_directory: Path,
        locale: str = "tr-TR",
        headless: bool = False,
        channel: str = "chrome",
        viewport_width: int = 1440,
        viewport_height: int = 1000,
        accept_language: str = "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    ) -> None:
        self.profile_directory = Path(profile_directory)
        self.locale = locale
        self.headless = headless
        self.channel = channel
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.accept_language = accept_language

    def download(
        self,
        url: str,
        security_detector: SecurityDetector | None = None,
        debug_file: Path | None = None,
        initial_wait_seconds: float = 5.0,
        navigation_timeout_ms: int = 60_000,
        scroll_page: bool = True,
        verification_title: str = "GÜVENLİK DOĞRULAMASI",
        verification_message: str | None = None,
    ) -> BrowserDownloadResult:
        self.profile_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        print("Chrome profil klasörü:")
        print(self.profile_directory)

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_directory),
                channel=self.channel,
                headless=self.headless,
                locale=self.locale,
                viewport={
                    "width": self.viewport_width,
                    "height": self.viewport_height,
                },
                extra_http_headers={
                    "Accept-Language": self.accept_language,
                },
                args=[
                    "--start-maximized",
                ],
            )

            try:
                page = self._get_or_create_page(
                    context=context,
                    target_url=url,
                )

                response = self._navigate(
                    context=context,
                    page=page,
                    url=url,
                    timeout_ms=navigation_timeout_ms,
                )

                status_code = (
                    response.status
                    if response is not None
                    else None
                )

                if status_code is not None:
                    print(
                        "Chrome HTTP:",
                        status_code,
                    )

                page = self._wait_and_recover_page(
                    context=context,
                    current_page=page,
                    target_url=url,
                    seconds=initial_wait_seconds,
                )

                html = self._read_content(
                    context=context,
                    page=page,
                    target_url=url,
                )

                if (
                    security_detector is not None
                    and security_detector(html)
                ):
                    self._wait_for_manual_verification(
                        title=verification_title,
                        message=verification_message,
                    )

                    page = self._recover_after_verification(
                        context=context,
                        current_page=page,
                        target_url=url,
                        timeout_ms=navigation_timeout_ms,
                    )

                    page = self._wait_and_recover_page(
                        context=context,
                        current_page=page,
                        target_url=url,
                        seconds=initial_wait_seconds,
                    )

                    html = self._read_content(
                        context=context,
                        page=page,
                        target_url=url,
                    )

                if scroll_page:
                    page = self._scroll_page(
                        context=context,
                        current_page=page,
                        target_url=url,
                    )

                html = self._read_content(
                    context=context,
                    page=page,
                    target_url=url,
                )

                title = self._read_title(page)
                final_url = self._read_url(page)

                if not self._urls_match_exactly(
                    final_url,
                    url,
                ):
                    raise RuntimeError(
                        "Ürün bağlantısı farklı bir sayfaya yönlendirildi. "
                        f"İstenen URL: {url} | Açılan URL: {final_url}"
                    )

                print(
                    "Chrome sayfa başlığı:",
                    title,
                )
                print(
                    "Chrome son URL:",
                    final_url,
                )
                print(
                    "Chrome sayfa uzunluğu:",
                    len(html),
                )

                if debug_file is not None:
                    self._save_debug_html(
                        debug_file=Path(debug_file),
                        html=html,
                    )

                return BrowserDownloadResult(
                    html=html,
                    title=title,
                    final_url=final_url,
                    status_code=status_code,
                )

            finally:
                self._close_context_safely(context)

    def _navigate(
        self,
        context: BrowserContext,
        page: Page,
        url: str,
        timeout_ms: int,
    ):
        page = self._ensure_live_page(
            context=context,
            current_page=page,
            target_url=url,
        )

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )

            final_url = self._read_url(page)
            if not self._urls_match_exactly(
                final_url,
                url,
            ):
                print("Hedef URL tekrar açılıyor:")
                print(url)
                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )

            return response
        except PlaywrightTimeoutError:
            print(
                "Sayfa açılışı zaman aşımına uğradı; "
                "yüklenen mevcut içerik kullanılacak."
            )
            return None
        except PlaywrightError as error:
            page = self._get_or_create_page(
                context=context,
                target_url=url,
            )

            if self._page_matches_target(
                page=page,
                target_url=url,
            ):
                print(
                    "İlk sekme kapandı veya değişti; "
                    "aktif sekme kullanılacak."
                )
                return None

            raise RuntimeError(
                "Chrome sayfasına gidilirken tarayıcı hedefi kapandı."
            ) from error

    def _wait_and_recover_page(
        self,
        context: BrowserContext,
        current_page: Page,
        target_url: str,
        seconds: float,
    ) -> Page:
        """
        page.wait_for_timeout yerine Python beklemesi kullanılır.

        Böylece bekleme sırasında sekme kapanırsa Playwright'ın kapalı
        Page nesnesi üzerinde işlem yapması engellenir.
        """

        time.sleep(max(0.0, seconds))

        return self._ensure_live_page(
            context=context,
            current_page=current_page,
            target_url=target_url,
        )

    def _recover_after_verification(
        self,
        context: BrowserContext,
        current_page: Page,
        target_url: str,
        timeout_ms: int,
    ) -> Page:
        page = self._ensure_live_page(
            context=context,
            current_page=current_page,
            target_url=target_url,
        )

        current_url = self._read_url(page).lower()

        should_navigate_again = (
            not current_url
            or current_url == "about:blank"
            or "security" in current_url
            or not self._same_domain(
                current_url,
                target_url,
            )
        )

        try:
            if should_navigate_again:
                page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )
            else:
                page.reload(
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )

        except PlaywrightTimeoutError:
            print(
                "Doğrulama sonrası sayfa yenilemesi "
                "zaman aşımına uğradı."
            )

        except PlaywrightError:
            page = self._get_or_create_page(
                context=context,
                target_url=target_url,
            )

            if not self._page_matches_target(
                page=page,
                target_url=target_url,
            ):
                page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=timeout_ms,
                )

        return self._ensure_live_page(
            context=context,
            current_page=page,
            target_url=target_url,
        )

    def _scroll_page(
        self,
        context: BrowserContext,
        current_page: Page,
        target_url: str,
    ) -> Page:
        page = current_page

        for _ in range(4):
            page = self._ensure_live_page(
                context=context,
                current_page=page,
                target_url=target_url,
            )

            try:
                page.mouse.wheel(
                    0,
                    1200,
                )
            except PlaywrightError:
                page = self._get_or_create_page(
                    context=context,
                    target_url=target_url,
                )

            time.sleep(0.75)

        page = self._ensure_live_page(
            context=context,
            current_page=page,
            target_url=target_url,
        )

        try:
            page.mouse.wheel(
                0,
                -4800,
            )
        except PlaywrightError:
            page = self._get_or_create_page(
                context=context,
                target_url=target_url,
            )

        time.sleep(1.0)

        return self._ensure_live_page(
            context=context,
            current_page=page,
            target_url=target_url,
        )

    def _read_content(
        self,
        context: BrowserContext,
        page: Page,
        target_url: str,
    ) -> str:
        page = self._ensure_live_page(
            context=context,
            current_page=page,
            target_url=target_url,
        )

        try:
            return page.content()
        except PlaywrightError as error:
            recovered_page = self._get_or_create_page(
                context=context,
                target_url=target_url,
            )

            try:
                return recovered_page.content()
            except PlaywrightError as second_error:
                raise RuntimeError(
                    "Chrome sayfa içeriği okunamadı; "
                    "sekme veya tarayıcı kapanmış olabilir."
                ) from second_error

    def _ensure_live_page(
        self,
        context: BrowserContext,
        current_page: Page | None,
        target_url: str,
    ) -> Page:
        if (
            current_page is not None
            and not self._is_page_closed(current_page)
        ):
            return current_page

        return self._get_or_create_page(
            context=context,
            target_url=target_url,
        )

    def _get_or_create_page(
        self,
        context: BrowserContext,
        target_url: str,
    ) -> Page:
        try:
            page = context.new_page()
            print("Yeni Chrome sekmesi açıldı.")
            return page
        except PlaywrightError as error:
            raise RuntimeError(
                "Chrome tarayıcı bağlamı kapandı. "
                "Tarayıcı penceresini test bitmeden kapatmayın."
            ) from error

    @staticmethod
    def _get_live_pages(
        context: BrowserContext,
    ) -> list[Page]:
        try:
            pages = list(context.pages)
        except PlaywrightError as error:
            raise RuntimeError(
                "Chrome tarayıcı bağlamına erişilemedi; "
                "tarayıcı kapanmış olabilir."
            ) from error

        return [
            page
            for page in pages
            if not BrowserEngine._is_page_closed(page)
        ]

    @staticmethod
    def _is_page_closed(
        page: Page,
    ) -> bool:
        try:
            return page.is_closed()
        except PlaywrightError:
            return True

    def _page_matches_target(
        self,
        page: Page,
        target_url: str,
    ) -> bool:
        page_url = self._read_url(page)

        if not page_url:
            return False

        page_parts = urlsplit(page_url)
        target_parts = urlsplit(target_url)

        page_host = (page_parts.hostname or "").lower()
        target_host = (target_parts.hostname or "").lower()

        if page_host != target_host:
            return False

        page_path = page_parts.path.rstrip("/").lower()
        target_path = target_parts.path.rstrip("/").lower()

        return page_path == target_path

    @staticmethod
    def _urls_match_exactly(
        first_url: str,
        second_url: str,
    ) -> bool:
        first_parts = urlsplit(first_url)
        second_parts = urlsplit(second_url)

        first_host = (first_parts.hostname or "").lower()
        second_host = (second_parts.hostname or "").lower()

        first_path = first_parts.path.rstrip("/").lower()
        second_path = second_parts.path.rstrip("/").lower()

        return (
            first_host == second_host
            and first_path == second_path
        )

    @staticmethod
    def _same_domain(
        first_url: str,
        second_url: str,
    ) -> bool:
        first_host = (
            urlsplit(first_url).hostname or ""
        ).lower()

        second_host = (
            urlsplit(second_url).hostname or ""
        ).lower()

        if not first_host or not second_host:
            return False

        return (
            first_host == second_host
            or first_host.endswith(
                f".{second_host}"
            )
            or second_host.endswith(
                f".{first_host}"
            )
        )

    @staticmethod
    def _read_url(
        page: Page,
    ) -> str:
        try:
            return str(page.url or "")
        except PlaywrightError:
            return ""

    @staticmethod
    def _read_title(
        page: Page,
    ) -> str:
        try:
            return page.title()
        except PlaywrightError:
            return ""

    @staticmethod
    def _wait_for_manual_verification(
        title: str,
        message: str | None,
    ) -> None:
        print()
        print("=" * 70)
        print(title)
        print("=" * 70)

        if message:
            print(message)
        else:
            print(
                "Tarayıcı penceresindeki güvenlik doğrulamasını "
                "tamamlayın."
            )

        print(
            "Ürün sayfası tamamen açıldıktan sonra "
            "PowerShell penceresine dönün."
        )
        print()

        input(
            "Doğrulama tamamlanınca Enter'a bas: "
        )

    @staticmethod
    def _save_debug_html(
        debug_file: Path,
        html: str,
    ) -> None:
        debug_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        debug_file.write_text(
            html,
            encoding="utf-8",
        )

        print(
            "Debug HTML oluşturuldu:"
        )
        print(debug_file)

    @staticmethod
    def _close_context_safely(
        context: BrowserContext,
    ) -> None:
        try:
            context.close()
        except PlaywrightError:
            pass
