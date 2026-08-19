from __future__ import annotations

import html as html_module
import re
import threading
import json
from datetime import datetime, timezone
from time import perf_counter
from dataclasses import fields, is_dataclass
from pathlib import Path
from urllib.parse import (
    parse_qs,
    quote_plus,
    unquote,
    urljoin,
    urlsplit,
    urlunsplit,
)

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.parsers.hepsiburada_parser import HepsiburadaParser
from app.scrapers.base import BaseScraper
from app.services.browser_engine import BrowserEngine
from app.services.scraper_runtime_config import SCRAPER_HEADLESS


class HepsiburadaSecurityChallenge(RuntimeError):
    """Hepsiburada normal ürün HTML'i yerine güvenlik doğrulaması gösterdi."""

    code = "SECURITY_CHALLENGE"


class HepsiburadaScraper(BaseScraper):
    _session_lock = threading.RLock()
    BASE_URL = "https://www.hepsiburada.com"

    SECURITY_TEXTS = (
        "hepsiburada | güvenlik",
        "hepsiburada | security",
        "hbblockandcaptcha",
        "akreferanceid",
        "security/hbblockandcaptcha",
    )

    def __init__(self) -> None:
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

        # V19: Tüm Hepsiburada okumaları aynı kalıcı Chrome profilini kullanır.
        self.profile_directory = (
            project_root / ".playwright-hepsiburada-profile"
        )
        # V20.9: Profil proje kökünde sabittir. Her taramada geçici
        # user-data-dir üretilmez; doğrulama sonrası Chrome cookie/local
        # storage verileri bu dizinde sonraki taramalara taşınır.
        self.profile_directory.mkdir(parents=True, exist_ok=True)

        self.debug_file = project_root / "hb_debug.html"
        self.session_metadata_file = project_root / "hb_session_metadata.json"

        self.search_debug_file = (
            project_root
            / "hb_search_debug.html"
        )

        self.web_search_debug_file = (
            project_root
            / "hb_web_search_debug.html"
        )

        self.bing_search_debug_file = (
            project_root
            / "hb_bing_search_debug.html"
        )

        self.google_search_debug_file = (
            project_root
            / "hb_google_search_debug.html"
        )

        self.browser_engine = BrowserEngine(
            profile_directory=self.profile_directory,
            locale="tr-TR",
            headless=SCRAPER_HEADLESS,
            channel="chrome",
            viewport_width=1440,
            viewport_height=1000,
            accept_language=self.headers["Accept-Language"],
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

        hostname = (parts.hostname or "").lower()

        if not (
            hostname == "hepsiburada.com"
            or hostname.endswith(".hepsiburada.com")
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
        Hepsiburada ürününü yalnızca kalıcı profilli gerçek Chrome ile okur.

        Akış:
        1. Verilen ürün bağlantısını açar.
        2. Sayfa başka yere yönlenirse ürün koduyla Hepsiburada'da arar.
        3. Arama sonuçlarındaki ürün bağlantılarını sırayla dener.
        4. Gerçek ürün HTML'ini parser'a gönderir.
        """

        clean_url = self.clean_product_url(url)

        print("Hepsiburada tarayıcı akışı başlatılıyor:")
        print(clean_url)

        try:
            return self._scrape_with_browser_navigation(clean_url)
        except HepsiburadaSecurityChallenge:
            raise
        except Exception as error:
            raise RuntimeError(
                "Hepsiburada ürünü tarayıcı üzerinden okunamadı. "
                f"Ayrıntı: {error}"
            ) from error

    def _scrape_with_browser_navigation(
        self,
        original_url: str,
    ):
        product_code = self._extract_product_code(original_url)
        product_name = self._extract_product_name_from_url(original_url)

        # V20.2: Aynı profilin eşzamanlı iki Chrome süreci tarafından
        # açılmasını engeller. Güvenlik doğrulaması tamamlanırsa cookie ve
        # local storage aynı kalıcı profilde sonraki taramalarda korunur.
        hb_total_started_v236213 = perf_counter()
        with self._session_lock, sync_playwright() as playwright:
            hb_launch_started_v236213 = perf_counter()
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_directory),
                channel="chrome",
                headless=SCRAPER_HEADLESS,
                locale="tr-TR",
                viewport={"width": 1440, "height": 1000},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
            )

            try:
                print(
                    f"V23.62.13 HB PHASE browser_launch="
                    f"{perf_counter() - hb_launch_started_v236213:.3f}s"
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(30_000)

                direct_error: Exception | None = None

                try:
                    return self._open_and_parse_product_page(
                        page=page,
                        candidate_url=original_url,
                        expected_product_code=product_code,
                    )
                except Exception as error:
                    direct_error = error
                    print("Doğrudan ürün sayfası okunamadı:", error)
                    if isinstance(error, HepsiburadaSecurityChallenge):
                        # V20.9: Aynı challenge oturumunda HB arama sayfasını
                        # veya başka aday URL'leri tekrar tekrar açma.
                        raise

                search_terms = [
                    term
                    for term in (product_code, product_name)
                    if term
                ]

                candidate_urls: list[str] = []

                for search_term in search_terms:
                    search_url = (
                        f"{self.BASE_URL}/ara?q="
                        f"{quote_plus(search_term)}"
                    )

                    print("Hepsiburada içinde aranıyor:")
                    print(search_url)

                    page.goto(
                        search_url,
                        wait_until="domcontentloaded",
                        timeout=60_000,
                    )
                    page.wait_for_timeout(5_000)

                    search_html = page.content()
                    self.search_debug_file.write_text(
                        search_html,
                        encoding="utf-8",
                    )

                    if self._is_security_page(search_html):
                        print(
                            "Güvenlik doğrulaması görünüyorsa Chrome'da tamamlayın. "
                            "Sonuç sayfası açıldığında işlem otomatik devam edecek."
                        )
                        page.wait_for_timeout(15_000)
                        search_html = page.content()

                    new_candidates = self._collect_product_links_from_page(
                        page=page,
                        expected_product_code=product_code,
                    )

                    for candidate in new_candidates:
                        if candidate not in candidate_urls:
                            candidate_urls.append(candidate)

                    if candidate_urls:
                        break

                if not candidate_urls:
                    raise LookupError(
                        "Hepsiburada arama sonuçlarında ürün bağlantısı bulunamadı. "
                        f"Doğrudan açma hatası: {direct_error}"
                    )

                candidate_errors: list[str] = []

                for index, candidate_url in enumerate(candidate_urls[:12], start=1):
                    print(
                        f"Ürün adayı deneniyor {index}/{min(len(candidate_urls), 12)}:"
                    )
                    print(candidate_url)

                    try:
                        return self._open_and_parse_product_page(
                            page=page,
                            candidate_url=candidate_url,
                            expected_product_code=product_code,
                        )
                    except Exception as error:
                        candidate_errors.append(
                            f"{candidate_url} -> {error}"
                        )

                raise RuntimeError(
                    "Bulunan ürün bağlantılarının hiçbiri okunamadı. "
                    + " | ".join(candidate_errors[:5])
                )

            finally:
                hb_pre_cleanup_total_v236244 = perf_counter() - hb_total_started_v236213
                hb_cleanup_started_v236244 = perf_counter()
                context.close()
                hb_cleanup_elapsed_v236244 = perf_counter() - hb_cleanup_started_v236244
                hb_total_elapsed_v236244 = perf_counter() - hb_total_started_v236213
                print(
                    f"V23.62.44 HB CHALLENGE PATH PHASE cleanup: "
                    f"elapsed={hb_cleanup_elapsed_v236244:.3f}s "
                    f"pre_cleanup_total={hb_pre_cleanup_total_v236244:.3f}s"
                )
                print(
                    f"V23.62.13 HB TOTAL="
                    f"{hb_total_elapsed_v236244:.3f}s"
                )
                print(
                    f"V23.62.44 HB CHALLENGE PATH PHASE total: "
                    f"elapsed={hb_total_elapsed_v236244:.3f}s"
                )

    def _open_and_parse_product_page(
        self,
        page,
        candidate_url: str,
        expected_product_code: str | None,
    ):
        requested_url = self.clean_product_url(candidate_url)

        hb_goto_started_v236213 = perf_counter()
        page.goto(
            requested_url,
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        hb_detail_goto_elapsed_v236244 = perf_counter() - hb_goto_started_v236213
        print(
            f"V23.62.13 HB PHASE goto="
            f"{hb_detail_goto_elapsed_v236244:.3f}s"
        )
        print(
            f"V23.62.44 HB CHALLENGE PATH PHASE detail_goto: "
            f"elapsed={hb_detail_goto_elapsed_v236244:.3f}s"
        )

        # V23.62.13: challenge ayrımı için 1 saniye settle yeterli;
        # ürün parse güvenliği sonraki HTML/URL kontrollerinde korunur.
        hb_settle_started_v236213 = perf_counter()
        page.wait_for_timeout(1_000)
        print(
            f"V23.62.13 HB PHASE settle="
            f"{perf_counter() - hb_settle_started_v236213:.3f}s"
        )

        current_url = page.url
        html = page.content()

        self.debug_file.write_text(
            html,
            encoding="utf-8",
        )

        print("Chrome açılan URL:", current_url)
        print("Chrome HTML uzunluğu:", len(html))

        hb_challenge_detection_started_v236244 = perf_counter()
        hb_challenge_detected_v236244 = self._is_security_page(html)
        hb_challenge_detection_elapsed_v236244 = perf_counter() - hb_challenge_detection_started_v236244
        print(
            f"V23.62.44 HB CHALLENGE PATH PHASE challenge_detection: "
            f"elapsed={hb_challenge_detection_elapsed_v236244:.3f}s "
            f"detected={hb_challenge_detected_v236244}"
        )

        if hb_challenge_detected_v236244:
            html = self._recover_from_security_page(
                page=page,
                requested_url=requested_url,
            )

        if self._is_security_page(html):
            raise HepsiburadaSecurityChallenge(
                "SECURITY_CHALLENGE: Hepsiburada güvenlik doğrulaması "
                "devam ediyor; ürün HTML'i scraper pipeline'ına gönderilmedi."
            )

        if not self._looks_like_product_url(current_url):
            raise RuntimeError(
                "Ürün sayfası yerine farklı bir sayfa açıldı. "
                f"Açılan URL: {current_url}"
            )

        if (
            expected_product_code
            and expected_product_code.lower() not in current_url.lower()
            and expected_product_code.lower() not in html.lower()
        ):
            raise RuntimeError(
                "Açılan ürün, istenen ürün koduyla eşleşmiyor. "
                f"Beklenen kod: {expected_product_code}"
            )

        if len(html) < 3_000:
            raise ValueError(
                "Ürün sayfasının HTML içeriği beklenenden kısa."
            )

        product = self._parse_product(
            html=html,
            url=self.clean_product_url(current_url),
        )
        product = self._repair_product_text(product)

        print("Ürün tarayıcıyla başarıyla okundu.")
        return product

    def _recover_from_security_page(
        self,
        page,
        requested_url: str,
    ) -> str:
        """V20.9 kalıcı oturum yöneticisi.

        Güvenlik mekanizmasını atlatmaz. Kullanıcı normal Chrome penceresinde
        doğrulamayı tamamladıysa aynı kalıcı profil/cookie oturumunda bunu
        kısa aralıklarla algılar. Challenge devam ediyorsa uzun reload
        zincirine girmeden çağırana SECURITY_CHALLENGE döndürülmesini sağlar.
        """

        last_html = page.content()
        print(
            "Hepsiburada SECURITY_CHALLENGE tespit edildi; "
            "kalıcı profil oturumu kısa süre kontrol ediliyor."
        )

        # V23.62.13: Güvenliği aşmadan challenge'ın kalkıp kalkmadığını
        # kısa bir pencereyle kontrol et. V23.63.20: mevcut 1s kontrolüne
        # yalnız bir 2s bounded recheck daha eklenir; challenge bypass edilmez.
        hb_challenge_started_v236213 = perf_counter()
        for attempt, wait_ms in enumerate((1_000, 2_000), start=1):
            page.wait_for_timeout(wait_ms)
            try:
                last_html = page.content()
            except Exception:
                last_html = ""

            if not self._is_security_page(last_html):
                # Challenge kalktıktan sonra asıl ürün URL'sine aynı oturumla
                # yalnızca bir kez dön.
                try:
                    if self.clean_product_url(page.url) != self.clean_product_url(requested_url):
                        page.goto(
                            requested_url,
                            wait_until="domcontentloaded",
                            timeout=30_000,
                        )
                        page.wait_for_timeout(2_000)
                        last_html = page.content()
                except Exception:
                    pass

                if (
                    not self._is_security_page(last_html)
                    and len(last_html) >= 3_000
                ):
                    print(
                        "Hepsiburada kalıcı oturumu doğrulandı; "
                        "ürün pipeline'ına devam ediliyor."
                    )
                    self._write_session_metadata(page, verified=True)
                    hb_challenge_recheck_elapsed_v236244 = perf_counter() - hb_challenge_started_v236213
                    print(
                        f"V23.62.13 HB PHASE challenge_recheck="
                        f"{hb_challenge_recheck_elapsed_v236244:.3f}s "
                        f"resolved=True"
                    )
                    print(
                        f"V23.62.44 HB CHALLENGE PATH PHASE challenge_recheck: "
                        f"elapsed={hb_challenge_recheck_elapsed_v236244:.3f}s resolved=True"
                    )
                    print(
                        f"V23.63.20 HB BOUNDED CHALLENGE RECHECK: "
                        f"attempt={attempt}/2 wait_ms={wait_ms} resolved=True bypass=False"
                    )
                    return last_html

            print(
                f"Hepsiburada challenge kontrolü {attempt}/2: "
                "doğrulama hâlâ aktif."
            )
            print(
                f"V23.63.20 HB BOUNDED CHALLENGE RECHECK: "
                f"attempt={attempt}/2 wait_ms={wait_ms} resolved=False bypass=False"
            )

        self._write_session_metadata(page, verified=False)
        hb_challenge_recheck_elapsed_v236244 = perf_counter() - hb_challenge_started_v236213
        print(
            f"V23.62.13 HB PHASE challenge_recheck="
            f"{hb_challenge_recheck_elapsed_v236244:.3f}s "
            f"resolved=False"
        )
        print(
            f"V23.62.44 HB CHALLENGE PATH PHASE challenge_recheck: "
            f"elapsed={hb_challenge_recheck_elapsed_v236244:.3f}s resolved=False"
        )
        print(
            "V23.63.20 HB BOUNDED CHALLENGE RECHECK EXHAUSTED: "
            "attempts=2 resolved=False bypass=False fail_closed=True"
        )
        return last_html

    def _write_session_metadata(self, page, *, verified: bool) -> None:
        """Oturum durumunu teşhis amacıyla kaydeder; güvenliği aşmaz."""
        try:
            cookies = page.context.cookies()
            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "verified": bool(verified),
                "url": page.url,
                "cookie_names": sorted({str(item.get("name", "")) for item in cookies if item.get("name")}),
            }
            self.session_metadata_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            return

    def _collect_product_links_from_page(
        self,
        page,
        expected_product_code: str | None,
    ) -> list[str]:
        links = page.locator("a[href]").evaluate_all(
            """elements => elements.map(element => element.href)"""
        )

        exact_matches: list[str] = []
        other_products: list[str] = []

        for raw_url in links:
            try:
                clean_url = self.clean_product_url(str(raw_url))
            except ValueError:
                continue

            if not self._looks_like_product_url(clean_url):
                continue

            if expected_product_code and expected_product_code.lower() in clean_url.lower():
                if clean_url not in exact_matches:
                    exact_matches.append(clean_url)
            elif clean_url not in other_products:
                other_products.append(clean_url)

        print("Arama sonuçlarında bulunan ürün bağlantısı:", len(exact_matches) + len(other_products))

        return exact_matches + other_products

    def _scrape_candidate_url(
        self,
        url: str,
    ):
        clean_url = self.clean_product_url(url)

        html = self._download_with_playwright(
            clean_url
        )

        return self._parse_product(
            html=html,
            url=clean_url,
        )

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

        print("Requests HTTP:", response.status_code)
        response.raise_for_status()

        final_url = self.clean_product_url(response.url)

        if final_url != self.clean_product_url(url):
            raise RuntimeError(
                "Requests ürün bağlantısını farklı bir sayfaya yönlendirdi. "
                f"İstenen URL: {url} | Açılan URL: {response.url}"
            )

        html = response.text

        print("Requests sayfa uzunluğu:", len(html))

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
        result = self.browser_engine.download(
            url=url,
            security_detector=self._is_security_page,
            debug_file=self.debug_file,
            initial_wait_seconds=5.0,
            navigation_timeout_ms=60_000,
            scroll_page=True,
            verification_title=(
                "HEPSİBURADA GÜVENLİK DOĞRULAMASI"
            ),
            verification_message=(
                "Güvenlik doğrulaması veya CAPTCHA görünüyorsa tamamlayın."
            ),
        )

        html = result.html

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

    def _find_replacement_product_url(
        self,
        original_url: str,
    ) -> str | None:
        product_code = self._extract_product_code(original_url)

        if not product_code:
            raise ValueError(
                "Bağlantıdan Hepsiburada ürün kodu çıkarılamadı."
            )

        search_url = (
            f"{self.BASE_URL}/ara?q="
            f"{quote_plus(product_code)}"
        )

        print("Ürün koduyla Hepsiburada araması yapılıyor:")
        print(search_url)

        result = self.browser_engine.download(
            url=search_url,
            security_detector=self._is_security_page,
            debug_file=self.search_debug_file,
            initial_wait_seconds=4.0,
            navigation_timeout_ms=60_000,
            scroll_page=False,
            verification_title=(
                "HEPSİBURADA ARAMA DOĞRULAMASI"
            ),
            verification_message=(
                "Güvenlik doğrulaması görünüyorsa tamamlayın."
            ),
        )

        return self._extract_matching_product_url(
            html=result.html,
            product_code=product_code,
            original_url=original_url,
        )

    def _find_product_urls_with_web_search(
        self,
        original_url: str,
    ) -> list[str]:
        product_code = self._extract_product_code(
            original_url
        )

        product_name = self._extract_product_name_from_url(
            original_url
        )

        queries: list[str] = []

        if product_code:
            queries.append(
                f'site:hepsiburada.com "{product_code}"'
            )

        if product_name:
            queries.append(
                f'site:hepsiburada.com "{product_name}"'
            )

        if not queries:
            raise ValueError(
                "Web araması için ürün kodu veya ürün adı çıkarılamadı."
            )

        found_urls: list[str] = []

        for query in queries:
            for engine_name, search_url in (
                (
                    "Bing",
                    "https://www.bing.com/search?q="
                    + quote_plus(query),
                ),
                (
                    "Google",
                    "https://www.google.com/search?q="
                    + quote_plus(query),
                ),
            ):
                print(
                    f"{engine_name} üzerinde ürün aranıyor:"
                )
                print(search_url)

                try:
                    search_html = self._download_search_page(
                        url=search_url,
                        engine_name=engine_name,
                    )
                except Exception as error:
                    print(
                        f"{engine_name} araması başarısız:",
                        error,
                    )
                    continue

                candidates = self._extract_hepsiburada_urls_from_search_html(
                    search_html
                )

                for candidate in candidates:
                    if candidate not in found_urls:
                        found_urls.append(candidate)

                if found_urls:
                    return found_urls[:10]

        return found_urls[:10]

    def _download_search_page(
        self,
        url: str,
        engine_name: str,
    ) -> str:
        """
        Arama motoru sayfasını önce requests ile dener.

        Google/Bing boş sonuç, JavaScript doğrulaması veya bot engeli
        döndürürse aynı URL kalıcı profilli Chrome ile açılır.
        """

        normalized_engine = str(engine_name or "").strip().lower()

        if normalized_engine == "bing":
            debug_file = self.bing_search_debug_file
        elif normalized_engine == "google":
            debug_file = self.google_search_debug_file
        else:
            debug_file = self.web_search_debug_file

        requests_error: Exception | None = None

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30,
                allow_redirects=True,
            )

            print(
                f"{engine_name} requests HTTP:",
                response.status_code,
            )

            response.raise_for_status()

            response.encoding = (
                response.apparent_encoding
                or response.encoding
                or "utf-8"
            )

            html = response.text

            debug_file.write_text(
                html,
                encoding="utf-8",
            )

            if len(html) < 1000:
                raise ValueError(
                    f"{engine_name} HTML içeriği beklenenden kısa."
                )

            if self._is_search_block_page(html):
                raise PermissionError(
                    f"{engine_name} requests isteğine doğrulama/engel sayfası döndürdü."
                )

            print(
                f"{engine_name} requests sayfa uzunluğu:",
                len(html),
            )

            return html

        except Exception as error:
            requests_error = error

            print(
                f"{engine_name} requests yöntemi başarısız:",
                error,
            )
            print(
                f"{engine_name} araması Chrome ile tekrar deneniyor..."
            )

        result = self.browser_engine.download(
            url=url,
            security_detector=self._is_search_block_page,
            debug_file=debug_file,
            initial_wait_seconds=5.0,
            navigation_timeout_ms=60_000,
            scroll_page=True,
            verification_title=(
                f"{engine_name.upper()} ARAMA DOĞRULAMASI"
            ),
            verification_message=(
                "Tarayıcıda CAPTCHA veya güvenlik doğrulaması görünüyorsa "
                "tamamlayın. Arama sonuçları açıldıktan sonra Enter'a basın."
            ),
        )

        html = result.html

        if len(html) < 1000:
            raise ValueError(
                f"{engine_name} Chrome HTML içeriği beklenenden kısa."
            )

        if self._is_search_block_page(html):
            raise PermissionError(
                f"{engine_name} Chrome üzerinde de doğrulama/engel sayfası gösteriyor. "
                f"Requests hatası: {requests_error}"
            )

        print(
            f"{engine_name} Chrome sayfa uzunluğu:",
            len(html),
        )

        return html

    @staticmethod
    def _is_search_block_page(
        html: str,
    ) -> bool:
        normalized = str(html or "").lower()

        block_markers = (
            "google search</title>",
            "google arama'ya erişme konusunda sorun",
            "httpservice/retry/enablejs",
            "emsg=sg_rel",
            "unusual traffic",
            "our systems have detected unusual traffic",
            "detected unusual traffic",
            "captcha",
            "bing.com/turing",
            "challenge",
        )

        # Normal Google sonuç sayfasında de title içinde Google Search olabilir.
        # Bu yüzden tek başına başlık değil, doğrulama belirteçleri aranır.
        strong_markers = (
            "httpservice/retry/enablejs",
            "google arama'ya erişme konusunda sorun",
            "emsg=sg_rel",
            "our systems have detected unusual traffic",
            "bing.com/turing",
        )

        if any(marker in normalized for marker in strong_markers):
            return True

        if "captcha" in normalized and "hepsiburada.com" not in normalized:
            return True

        return False

    def _extract_hepsiburada_urls_from_search_html(
        self,
        html: str,
    ) -> list[str]:
        normalized_html = html_module.unescape(
            str(html or "")
        )

        normalized_html = (
            normalized_html
            .replace("\\u002F", "/")
            .replace("\\u002f", "/")
            .replace("\\/", "/")
        )

        raw_candidates: list[str] = []

        direct_pattern = (
            r'https?://(?:www\.)?hepsiburada\.com/'
            r'[^"\'<>\s&]+'
        )

        raw_candidates.extend(
            re.findall(
                direct_pattern,
                normalized_html,
                flags=re.IGNORECASE,
            )
        )

        href_pattern = r'href=["\']([^"\']+)["\']'

        for href in re.findall(
            href_pattern,
            normalized_html,
            flags=re.IGNORECASE,
        ):
            decoded_href = html_module.unescape(
                unquote(href)
            )

            if "hepsiburada.com" in decoded_href.lower():
                raw_candidates.append(decoded_href)

            parsed = urlsplit(decoded_href)
            query_values = parse_qs(parsed.query)

            for key in ("url", "u", "q"):
                for value in query_values.get(key, []):
                    decoded_value = unquote(value)

                    if (
                        "hepsiburada.com"
                        in decoded_value.lower()
                    ):
                        raw_candidates.append(
                            decoded_value
                        )

        clean_candidates: list[str] = []

        for candidate in raw_candidates:
            candidate = self._extract_embedded_hepsiburada_url(
                candidate
            )

            if not candidate:
                continue

            candidate = candidate.rstrip(
                "\\,;)}]\"'"
            )

            try:
                clean_candidate = self.clean_product_url(
                    candidate
                )
            except ValueError:
                continue

            if not self._looks_like_product_url(
                clean_candidate
            ):
                continue

            if clean_candidate not in clean_candidates:
                clean_candidates.append(clean_candidate)

        return clean_candidates

    @staticmethod
    def _extract_embedded_hepsiburada_url(
        value: str,
    ) -> str | None:
        value = html_module.unescape(
            unquote(str(value or ""))
        )

        match = re.search(
            r'https?://(?:www\.)?hepsiburada\.com/'
            r'[^"\'<>\s&]+',
            value,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(0)

    @staticmethod
    def _looks_like_product_url(
        url: str,
    ) -> bool:
        path = urlsplit(url).path.lower()

        return bool(
            re.search(
                r'(?:^|[-/])pm?-[a-z0-9]+(?:$|[/?#-])',
                path,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _extract_product_code(
        url: str,
    ) -> str | None:
        match = re.search(
            r"(?:^|[-/])pm?-([A-Za-z0-9]+)(?:$|[/?#-])",
            urlsplit(url).path,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        return match.group(1).upper()

    @staticmethod
    def _extract_product_name_from_url(
        url: str,
    ) -> str | None:
        path = urlsplit(url).path.strip("/")

        if not path:
            return None

        slug = re.sub(
            r"-pm?-[A-Za-z0-9]+.*$",
            "",
            path,
            flags=re.IGNORECASE,
        )

        words = [
            word
            for word in slug.split("-")
            if len(word) > 1
        ]

        if not words:
            return None

        return " ".join(words[:14])

    def _extract_matching_product_url(
        self,
        html: str,
        product_code: str,
        original_url: str,
    ) -> str | None:
        normalized_html = html_module.unescape(
            str(html or "")
        )

        normalized_html = (
            normalized_html
            .replace("\\u002F", "/")
            .replace("\\u002f", "/")
            .replace("\\/", "/")
        )

        code_pattern = re.escape(product_code)

        patterns = (
            rf'https?://[^"\'<>\s]+[-/]p-{code_pattern}[^"\'<>\s]*',
            rf'["\'](/[^"\']+[-/]p-{code_pattern}[^"\']*)["\']',
        )

        candidates: list[str] = []

        for pattern in patterns:
            for match in re.findall(
                pattern,
                normalized_html,
                flags=re.IGNORECASE,
            ):
                candidate = str(match).strip()
                candidate = candidate.rstrip(
                    "\\,;)}]"
                )

                absolute_url = urljoin(
                    self.BASE_URL,
                    candidate,
                )

                try:
                    clean_candidate = self.clean_product_url(
                        absolute_url
                    )
                except ValueError:
                    continue

                if (
                    product_code.lower()
                    not in clean_candidate.lower()
                ):
                    continue

                if clean_candidate not in candidates:
                    candidates.append(clean_candidate)

        original_clean = self.clean_product_url(
            original_url
        )

        for candidate in candidates:
            if candidate != original_clean:
                return candidate

        if candidates:
            return candidates[0]

        return None

    def _is_security_page(
        self,
        html: str,
    ) -> bool:
        normalized_html = self._normalize_turkish_text(
            str(html or "").lower()
        )

        normalized_security_texts = (
            self._normalize_turkish_text(text.lower())
            for text in self.SECURITY_TEXTS
        )

        return any(
            text in normalized_html
            for text in normalized_security_texts
        )

    @staticmethod
    def _normalize_turkish_text(
        text: str,
    ) -> str:
        return (
            text
            .replace("ü", "u")
            .replace("ı", "i")
            .replace("ş", "s")
            .replace("ğ", "g")
            .replace("ö", "o")
            .replace("ç", "c")
            .replace("İ", "i")
        )


    @classmethod
    def _repair_product_text(cls, product):
        """Parser çıktısındaki UTF-8/Latin-1 mojibake metinlerini düzeltir."""

        # Pydantic v2 modelleri
        if hasattr(product, "model_dump") and hasattr(product, "model_copy"):
            raw_data = product.model_dump()
            repaired_data = cls._repair_text_value(raw_data)
            repaired_product = product.model_copy(update=repaired_data)

            print(
                "Açıklama encoding kontrolü:",
                repr(raw_data.get("description")),
                "->",
                repr(repaired_data.get("description")),
            )
            return repaired_product

        # Pydantic v1 modelleri
        if hasattr(product, "dict") and hasattr(product, "copy"):
            try:
                raw_data = product.dict()
                repaired_data = cls._repair_text_value(raw_data)
                repaired_product = product.copy(update=repaired_data)

                print(
                    "Açıklama encoding kontrolü:",
                    repr(raw_data.get("description")),
                    "->",
                    repr(repaired_data.get("description")),
                )
                return repaired_product
            except TypeError:
                pass

        # Dataclass modelleri
        if is_dataclass(product):
            for field in fields(product):
                current_value = getattr(product, field.name)
                repaired_value = cls._repair_text_value(current_value)
                try:
                    setattr(product, field.name, repaired_value)
                except (AttributeError, TypeError):
                    object.__setattr__(product, field.name, repaired_value)
            return product

        # NamedTuple benzeri modeller
        if hasattr(product, "_asdict") and hasattr(product, "_replace"):
            raw_data = product._asdict()
            repaired_data = cls._repair_text_value(raw_data)
            return product._replace(**repaired_data)

        # Normal Python nesneleri
        if hasattr(product, "__dict__"):
            for name, current_value in vars(product).items():
                repaired_value = cls._repair_text_value(current_value)
                try:
                    setattr(product, name, repaired_value)
                except (AttributeError, TypeError):
                    try:
                        object.__setattr__(product, name, repaired_value)
                    except (AttributeError, TypeError):
                        pass

        return product

    @classmethod
    def _repair_text_value(cls, value):
        if isinstance(value, str):
            return cls._repair_mojibake(value)

        if isinstance(value, dict):
            return {
                cls._repair_text_value(key): cls._repair_text_value(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [cls._repair_text_value(item) for item in value]

        if isinstance(value, tuple):
            return tuple(cls._repair_text_value(item) for item in value)

        return value

    @staticmethod
    def _repair_mojibake(value: str) -> str:
        text = html_module.unescape(str(value or ""))

        # Hepsiburada meta açıklamalarında görülen özel bozulmalar.
        # "ű" dizisi standart dönüşümde "ű" olur; önce doğru mojibake
        # dizisine çevrilerek Türkçe "ı" elde edilir.
        text = (
            text
            .replace("ű", "ı")
            .replace("ş", "ş")
            .replace("ğ", "ğ")
        )

        suspicious_markers = (
            "Ãƒ", "Ã„", "Ã…", "Ã‚", "Ã¢â‚¬", "’", "Ã¢â‚¬Å“", "”", "ðŸ"
        )

        for _ in range(3):
            if not any(marker in text for marker in suspicious_markers):
                break

            repaired = None

            for source_encoding in ("latin-1", "cp1252"):
                try:
                    candidate = text.encode(source_encoding).decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue

                repaired = candidate
                break

            if repaired is None or repaired == text:
                break

            text = repaired

        # Bozuk veya eksik meta açıklama sonlarını temizle.
        text = re.sub(
            r"\s+[ıi]nıza\s+gelsin!?\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(r"\s+", " ", text)

        return text.strip()

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

