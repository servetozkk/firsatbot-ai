from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import quote_plus, urljoin, urlsplit, urlunsplit

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.sync_api import sync_playwright

from app.models.product import Product
from app.services.product_identity_service import (
    ProductIdentityService,
)
from app.services.product_service import save_product
from app.services.scraper_registry import ScraperRegistry


@dataclass(slots=True)
class StoreScanResult:
    store_code: str
    store_name: str
    success: bool
    message: str
    product_url: str | None = None
    match_score: float | None = None
    product: Any | None = None


@dataclass(slots=True)
class CrossStoreScanResult:
    source_store_code: str | None
    source_product_name: str
    searched_store_count: int = 0
    saved_offer_count: int = 0
    results: list[StoreScanResult] = field(
        default_factory=list
    )


@dataclass(frozen=True, slots=True)
class StoreSearchDefinition:
    code: str
    name: str
    base_url: str
    search_url_template: str
    product_path_patterns: tuple[str, ...]


STORE_SEARCH_DEFINITIONS = (
    StoreSearchDefinition(
        code="trendyol",
        name="Trendyol",
        base_url="https://www.trendyol.com",
        search_url_template="https://www.trendyol.com/sr?q={query}",
        product_path_patterns=("-p-",),
    ),
    StoreSearchDefinition(
        code="hepsiburada",
        name="Hepsiburada",
        base_url="https://www.hepsiburada.com",
        search_url_template="https://www.hepsiburada.com/ara?q={query}",
        product_path_patterns=("-p-", "-pm-"),
    ),
    StoreSearchDefinition(
        code="amazon",
        name="Amazon Türkiye",
        base_url="https://www.amazon.com.tr",
        search_url_template="https://www.amazon.com.tr/s?k={query}",
        product_path_patterns=("/dp/", "/gp/product/", "/product/"),
    ),
    StoreSearchDefinition(
        code="n11",
        name="N11",
        base_url="https://www.n11.com",
        search_url_template="https://www.n11.com/arama?q={query}",
        product_path_patterns=("/urun/",),
    ),
    StoreSearchDefinition(
        code="pazarama",
        name="Pazarama",
        base_url="https://www.pazarama.com",
        search_url_template="https://www.pazarama.com/arama?q={query}",
        product_path_patterns=("/urun/",),
    ),
    StoreSearchDefinition(
        code="idefix",
        name="İdefix",
        base_url="https://www.idefix.com",
        search_url_template="https://www.idefix.com/ara?q={query}",
        product_path_patterns=("/urun/",),
    ),
    StoreSearchDefinition(
        code="teknosa",
        name="Teknosa",
        base_url="https://www.teknosa.com",
        search_url_template="https://www.teknosa.com/arama/?s={query}",
        product_path_patterns=("-p-", "/urun/"),
    ),
    StoreSearchDefinition(
        code="mediamarkt",
        name="MediaMarkt",
        base_url="https://www.mediamarkt.com.tr",
        search_url_template=(
            "https://www.mediamarkt.com.tr/tr/search.html?query={query}"
        ),
        product_path_patterns=("/product/", "-p-"),
    ),
    StoreSearchDefinition(
        code="vatan",
        name="Vatan Bilgisayar",
        base_url="https://www.vatanbilgisayar.com",
        search_url_template=(
            "https://www.vatanbilgisayar.com/arama/{query}/"
        ),
        product_path_patterns=("/",),
    ),
    StoreSearchDefinition(
        code="itopya",
        name="İtopya",
        base_url="https://www.itopya.com",
        search_url_template=(
            "https://www.itopya.com/AramaSonuclari.aspx?text={query}"
        ),
        product_path_patterns=("/",),
    ),
    StoreSearchDefinition(
        code="incehesap",
        name="İncehesap",
        base_url="https://www.incehesap.com",
        search_url_template="https://www.incehesap.com/ara/?q={query}",
        product_path_patterns=("/",),
    ),
    StoreSearchDefinition(
        code="gaminggen",
        name="Gaming.Gen.TR",
        base_url="https://www.gaming.gen.tr",
        search_url_template=(
            "https://www.gaming.gen.tr/?s={query}&post_type=product"
        ),
        product_path_patterns=("/",),
    ),
)


class CrossStoreSearchService:
    """
    Kaynak ürünü diğer mağazalarda arar, güçlü biçimde
    eşleşen adayları tarar ve mevcut kayıt altyapısıyla
    veritabanına kaydeder.

    Tanımlı mağazaları sınırlı sayıda worker ile paralel
    tarar ve eşleşen teklifleri kaydeder.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        registry: ScraperRegistry | None = None,
        candidate_limit: int = 4,
        minimum_match_score: float = 0.78,
        parallel_workers: int = 4,
    ) -> None:
        self.registry = registry or ScraperRegistry()
        self.candidate_limit = max(
            1,
            min(int(candidate_limit), 12),
        )
        self.minimum_match_score = max(
            0.50,
            min(float(minimum_match_score), 1.0),
        )
        # Çok fazla eş zamanlı Chrome penceresi bilgisayarı
        # zorlayabileceği için güvenli bir üst sınır kullanılır.
        self.parallel_workers = max(
            1,
            min(int(parallel_workers), 6),
        )

    def scan_other_stores(
        self,
        source_product: Product,
    ) -> CrossStoreScanResult:
        source_store_code = self._detect_source_store(
            source_product
        )

        result = CrossStoreScanResult(
            source_store_code=source_store_code,
            source_product_name=source_product.name,
        )

        search_query = self._build_search_query(
            source_product
        )

        definitions = [
            definition
            for definition in STORE_SEARCH_DEFINITIONS
            if definition.code != source_store_code
        ]

        result.searched_store_count = len(definitions)

        print()
        print("=" * 70)
        print("PARALEL ÇOKLU MAĞAZA TARAMASI")
        print("=" * 70)
        print("Kaynak ürün:", source_product.name)
        print("Arama sorgusu:", search_query)
        print("Taranacak mağaza:", len(definitions))
        print("Eş zamanlı çalışan:", self.parallel_workers)

        indexed_results: dict[int, StoreScanResult] = {}

        with ThreadPoolExecutor(
            max_workers=self.parallel_workers,
            thread_name_prefix="store-scan",
        ) as executor:
            future_map = {
                executor.submit(
                    self._scan_store,
                    definition,
                    source_product,
                    search_query,
                ): (index, definition)
                for index, definition in enumerate(definitions)
            }

            for future in as_completed(future_map):
                index, definition = future_map[future]

                try:
                    store_result = future.result()
                except Exception as error:
                    store_result = StoreScanResult(
                        store_code=definition.code,
                        store_name=definition.name,
                        success=False,
                        message=(
                            "Mağaza taraması beklenmeyen hata verdi: "
                            f"{type(error).__name__}: {error}"
                        ),
                    )

                indexed_results[index] = store_result

                status = (
                    "BAŞARILI"
                    if store_result.success
                    else "BAŞARISIZ"
                )

                print(
                    f"[{status}] {store_result.store_name}: "
                    f"{store_result.message}"
                )

        # Sonuçlar, paralel bitiş sırasına göre değil mağaza
        # tanımlarındaki sabit sıraya göre döndürülür.
        result.results = [
            indexed_results[index]
            for index in range(len(definitions))
        ]

        result.saved_offer_count = sum(
            1
            for item in result.results
            if item.success
        )

        print()
        print("=" * 70)
        print("PARALEL TARAMA TAMAMLANDI")
        print("=" * 70)
        print("Taranan mağaza:", result.searched_store_count)
        print("Kaydedilen teklif:", result.saved_offer_count)

        return result

    def _scan_store(
        self,
        definition: StoreSearchDefinition,
        source_product: Product,
        search_query: str,
    ) -> StoreScanResult:
        print()
        print("-" * 70)
        print(f"{definition.name} mağazasında aranıyor...")
        print("-" * 70)

        try:
            candidate_urls = self._find_candidate_urls(
                definition=definition,
                search_query=search_query,
            )
        except Exception as error:
            return StoreScanResult(
                store_code=definition.code,
                store_name=definition.name,
                success=False,
                message=(
                    "Arama sonuçları alınamadı: "
                    f"{type(error).__name__}: {error}"
                ),
            )

        if not candidate_urls:
            return StoreScanResult(
                store_code=definition.code,
                store_name=definition.name,
                success=False,
                message="Ürün adayı bulunamadı.",
            )

        candidate_errors: list[str] = []
        best_rejected_score = 0.0
        best_rejected_url: str | None = None

        for index, candidate_url in enumerate(
            candidate_urls,
            start=1,
        ):
            print(
                f"[{index}/{len(candidate_urls)}] "
                f"Aday taranıyor: {candidate_url}"
            )

            try:
                # Her paralel görev kendi registry örneğini kullanır.
                # Böylece scraper nesneleri thread'ler arasında paylaşılmaz.
                local_registry = ScraperRegistry()

                candidate_product = local_registry.scrape(
                    candidate_url
                )

                if candidate_product is None:
                    candidate_errors.append(
                        f"{candidate_url}: ürün bilgisi yok"
                    )
                    continue

                is_match, score, reason = (
                    self._is_same_product(
                        source_product=source_product,
                        candidate_product=candidate_product,
                    )
                )

                print(
                    "Eşleşme:",
                    f"{score:.3f}",
                    reason,
                )

                if not is_match:
                    if score > best_rejected_score:
                        best_rejected_score = score
                        best_rejected_url = candidate_url
                    continue

                save_product(candidate_product)

                return StoreScanResult(
                    store_code=definition.code,
                    store_name=definition.name,
                    success=True,
                    message=(
                        "Eşleşen ürün bulundu ve teklif "
                        "olarak kaydedildi."
                    ),
                    product_url=candidate_product.url,
                    match_score=round(score, 3),
                    product=candidate_product,
                )

            except Exception as error:
                error_message = (
                    f"{candidate_url}: "
                    f"{type(error).__name__}: {error}"
                )
                candidate_errors.append(error_message)
                print("Aday tarama hatası:", error_message)

        if best_rejected_url:
            message = (
                "Adaylar bulundu fakat güvenli eşleşme "
                "eşiğini geçemedi. En yüksek skor: "
                f"{best_rejected_score:.3f}"
            )
        elif candidate_errors:
            message = (
                "Aday ürünler taranamadı. "
                + " | ".join(candidate_errors[:3])
            )
        else:
            message = "Uygun ürün eşleşmesi bulunamadı."

        return StoreScanResult(
            store_code=definition.code,
            store_name=definition.name,
            success=False,
            message=message,
            product_url=best_rejected_url,
            match_score=(
                round(best_rejected_score, 3)
                if best_rejected_score
                else None
            ),
        )

    def _find_candidate_urls(
        self,
        definition: StoreSearchDefinition,
        search_query: str,
    ) -> list[str]:
        search_url = definition.search_url_template.format(
            query=quote_plus(search_query)
        )

        print("Arama URL:", search_url)

        links: list[str] = []
        seen: set[str] = set()

        with sync_playwright() as playwright:
            # Hepsiburada ve Amazon headless tarayıcıyı sık
            # engellediği için gerçek Chrome görünür açılır.
            browser = playwright.chromium.launch(
                headless=False,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
            )

            page = browser.new_page(
                user_agent=self.USER_AGENT,
                locale="tr-TR",
                viewport={
                    "width": 1440,
                    "height": 1100,
                },
            )

            try:
                page.goto(
                    search_url,
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )

                page.wait_for_timeout(4_000)

                for _ in range(3):
                    page.mouse.wheel(0, 1300)
                    page.wait_for_timeout(700)

                try:
                    page.wait_for_load_state(
                        "networkidle",
                        timeout=8_000,
                    )
                except PlaywrightTimeoutError:
                    pass

                hrefs = page.locator(
                    "a[href]"
                ).evaluate_all(
                    """
                    elements => elements
                        .map(element => element.href)
                        .filter(Boolean)
                    """
                )

                for raw_url in hrefs:
                    clean_url = self._clean_candidate_url(
                        definition=definition,
                        url=str(raw_url),
                    )

                    if not clean_url:
                        continue

                    if clean_url in seen:
                        continue

                    seen.add(clean_url)
                    links.append(clean_url)

                    if len(links) >= self.candidate_limit:
                        break

            finally:
                browser.close()

        print("Bulunan aday sayısı:", len(links))
        return links

    def _clean_candidate_url(
        self,
        definition: StoreSearchDefinition,
        url: str,
    ) -> str | None:
        absolute_url = urljoin(
            definition.base_url,
            str(url or "").strip(),
        )

        parts = urlsplit(absolute_url)
        hostname = (parts.hostname or "").lower()

        expected_hostname = (
            urlsplit(definition.base_url).hostname or ""
        ).lower()

        bare_expected = expected_hostname.removeprefix("www.")
        bare_hostname = hostname.removeprefix("www.")

        if not (
            bare_hostname == bare_expected
            or bare_hostname.endswith(f".{bare_expected}")
        ):
            return None

        path = parts.path or "/"
        path_lower = path.lower()

        excluded_path_parts = (
            "/arama",
            "/search",
            "/sr",
            "/kategori",
            "/category",
            "/marka",
            "/brand",
            "/kampanya",
            "/campaign",
            "/sepet",
            "/cart",
            "/hesabim",
            "/account",
            "/magaza",
            "/store",
            "/yardim",
            "/help",
            "/blog",
        )

        if any(
            path_lower == excluded
            or path_lower.startswith(excluded + "/")
            for excluded in excluded_path_parts
        ):
            return None

        if definition.code == "amazon":
            asin_match = re.search(
                r"/(?:dp|gp/product|product)/"
                r"([A-Z0-9]{10})(?:[/?]|$)",
                path,
                flags=re.IGNORECASE,
            )

            if not asin_match:
                return None

            asin = asin_match.group(1).upper()
            return f"https://www.amazon.com.tr/dp/{asin}"

        if definition.code == "vatan":
            # Vatan ürün sayfaları çoğunlukla .html ile biter.
            if not path_lower.endswith(".html"):
                return None

        elif definition.code in {
            "itopya",
            "incehesap",
            "gaminggen",
        }:
            # Bu mağazalarda ürün yolları değişebildiği için,
            # yeterli uzunluk ve dosya/ürün benzeri yol aranır.
            path_segments = [
                segment
                for segment in path_lower.split("/")
                if segment
            ]

            if len(path_segments) < 1:
                return None

            if path_lower in {"/", ""}:
                return None

        elif not any(
            marker in path_lower
            for marker in definition.product_path_patterns
        ):
            return None

        return urlunsplit(
            (
                parts.scheme or "https",
                parts.netloc,
                path,
                "",
                "",
            )
        )

    @staticmethod
    def _detect_source_store(
        product: Product,
    ) -> str | None:
        source_site = str(
            product.source_site or ""
        ).strip().casefold()

        url_host = (
            urlsplit(product.url).hostname or ""
        ).casefold()

        if "trendyol" in source_site or (
            "trendyol.com" in url_host
        ):
            return "trendyol"

        if "hepsiburada" in source_site or (
            "hepsiburada.com" in url_host
        ):
            return "hepsiburada"

        if "amazon" in source_site or (
            "amazon.com.tr" in url_host
        ):
            return "amazon"

        return None

    @classmethod
    def _build_search_query(
        cls,
        product: Product,
    ) -> str:
        brand = str(product.brand or "").strip()
        model = (
            ProductIdentityService.get_normalized_model(
                product
            )
        )

        normalized_name = (
            ProductIdentityService.normalize_token(
                product.name
            )
        )

        query_parts: list[str] = []
        seen_tokens: set[str] = set()

        def add_value(value: str | None) -> None:
            for token in str(value or "").split():
                normalized_token = token.casefold().strip()

                if (
                    not normalized_token
                    or normalized_token in seen_tokens
                ):
                    continue

                seen_tokens.add(normalized_token)
                query_parts.append(token)

        add_value(brand)
        add_value(model)

        if len(query_parts) < 3:
            add_value(normalized_name)

        return " ".join(query_parts[:10]).strip()

    @classmethod
    def _is_same_product(
        cls,
        source_product: Product,
        candidate_product: Product,
    ) -> tuple[bool, float, str]:
        source_brand = (
            ProductIdentityService.normalize_token(
                source_product.brand
            )
        )
        candidate_brand = (
            ProductIdentityService.normalize_token(
                candidate_product.brand
            )
        )

        if (
            source_brand
            and candidate_brand
            and source_brand != candidate_brand
        ):
            return False, 0.0, "Marka farklı."

        source_model = (
            ProductIdentityService.get_normalized_model(
                source_product
            )
        )
        candidate_model = (
            ProductIdentityService.get_normalized_model(
                candidate_product
            )
        )

        model_exact = bool(
            source_model
            and candidate_model
            and source_model == candidate_model
        )

        source_tokens = set(
            ProductIdentityService.normalize_token(
                source_product.name
            ).split()
        )
        candidate_tokens = set(
            ProductIdentityService.normalize_token(
                candidate_product.name
            ).split()
        )

        union = source_tokens | candidate_tokens
        intersection = source_tokens & candidate_tokens

        token_score = (
            len(intersection) / len(union)
            if union
            else 0.0
        )

        sequence_score = SequenceMatcher(
            None,
            " ".join(sorted(source_tokens)),
            " ".join(sorted(candidate_tokens)),
        ).ratio()

        model_score = 1.0 if model_exact else 0.0

        if (
            source_model
            and candidate_model
            and not model_exact
        ):
            model_score = SequenceMatcher(
                None,
                source_model,
                candidate_model,
            ).ratio()

            if model_score < 0.86:
                return (
                    False,
                    round(model_score * 0.55, 3),
                    "Model kodu farklı.",
                )

        source_protected = set(
            cls._extract_protected_tokens(
                source_product.name
            )
        )
        candidate_protected = set(
            cls._extract_protected_tokens(
                candidate_product.name
            )
        )

        conflicting_tokens = (
            source_protected
            and candidate_protected
            and source_protected != candidate_protected
        )

        if conflicting_tokens:
            return (
                False,
                0.25,
                "Kapasite/ölçü/varyant bilgisi farklı.",
            )

        score = (
            token_score * 0.40
            + sequence_score * 0.25
            + model_score * 0.35
        )

        # Model iki tarafta da kesin aynıysa isimlerdeki mağaza
        # gürültüsünden dolayı oluşan küçük farklara tolerans tanınır.
        if model_exact:
            score = max(score, 0.90)

        matched = score >= 0.78

        return (
            matched,
            round(score, 3),
            (
                "Güvenli ürün eşleşmesi."
                if matched
                else "Benzerlik puanı yetersiz."
            ),
        )

    @staticmethod
    def _extract_protected_tokens(
        value: str | None,
    ) -> list[str]:
        """
        Yanlış varyantların aynı gruba girmesini önlemek için
        kapasite, ekran ölçüsü ve belirgin varyantları çıkarır.
        """
        text = (
            ProductIdentityService.normalize_token(
                value
            )
        )

        patterns = (
            r"\b\d+(?:[.,]\d+)?\s*(?:tb|gb|mb)\b",
            r"\b\d+(?:[.,]\d+)?\s*(?:inc|inch)\b",
            r"\b\d+(?:[.,]\d+)?\s*in\b",
            r"\b\d+\s*(?:hz|mah|w)\b",
        )

        tokens: list[str] = []

        for pattern in patterns:
            for match in re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                normalized = re.sub(
                    r"\s+",
                    "",
                    match.casefold(),
                ).replace(",", ".")

                if normalized not in tokens:
                    tokens.append(normalized)

        return tokens


_service = CrossStoreSearchService()


def scan_other_stores(
    source_product: Product,
) -> CrossStoreScanResult:
    return _service.scan_other_stores(
        source_product
    )