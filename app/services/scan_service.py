from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from app.services.cross_store_search_service import (
    CrossStoreScanResult,
    CrossStoreSearchService,
)
from app.services.product_service import save_product
from app.services.scraper_registry import (
    ScraperNotImplementedError,
    ScraperRegistry,
    UnsupportedStoreError,
)


@dataclass(slots=True)
class ScanResult:
    success: bool
    message: str
    store_code: str | None = None
    store_name: str | None = None
    product: Any | None = None
    cross_store_result: CrossStoreScanResult | None = None
    warnings: list[str] = field(default_factory=list)


_registry = ScraperRegistry()

# Aynı anda en fazla iki ayrı ürün için mağaza taraması çalışır.
# Böylece bilgisayar onlarca Chrome penceresiyle aşırı yüklenmez.
_background_executor = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="cross-store-scan",
)


def get_scraper_registry() -> ScraperRegistry:
    """
    Uygulama genelinde kullanılan ortak ScraperRegistry
    nesnesini döndürür.
    """
    return _registry


def _get_store_status(
    store_code: str,
) -> tuple[bool, bool]:
    """
    Registry içindeki mağazanın scraper durumunu döndürür.

    Returns:
        implemented: Scraper yazılmış mı?
        enabled: Scraper aktif mi?
    """
    for store in _registry.list_stores():
        if store.get("code") == store_code:
            return (
                bool(store.get("implemented", False)),
                bool(store.get("enabled", False)),
            )

    return False, False


def validate_product_url(
    url: str,
) -> tuple[bool, str]:
    """
    URL'nin desteklenen ve aktif bir mağazaya ait
    olup olmadığını kontrol eder.
    """
    normalized_url = url.strip()

    if not normalized_url:
        return (
            False,
            "Ürün bağlantısı boş bırakılamaz.",
        )

    try:
        store_definition = _registry.detect_store(
            normalized_url
        )

        implemented, enabled = _get_store_status(
            store_definition.code
        )

        if not implemented:
            return (
                False,
                f"{store_definition.name} scraper'ı "
                "henüz hazır değil.",
            )

        if not enabled:
            return (
                False,
                f"{store_definition.name} scraper'ı "
                "şu anda pasif.",
            )

        return (
            True,
            f"Geçerli {store_definition.name} "
            "ürün bağlantısı.",
        )

    except UnsupportedStoreError as error:
        return False, str(error)

    except Exception as error:
        return (
            False,
            "Ürün bağlantısı doğrulanırken hata oluştu: "
            f"{type(error).__name__}: {error}",
        )


def _scan_other_stores_in_background(
    product: Any,
) -> None:
    """
    Diğer mağaza taramasını HTTP isteğinden bağımsız
    bir arka plan iş parçacığında çalıştırır.

    Her görev kendi servis ve registry nesnesini kullanır.
    Böylece eş zamanlı taramalarda ortak scraper örneklerinin
    birbirine karışması önlenir.
    """
    try:
        print()
        print("=" * 70)
        print("ARKA PLAN MAĞAZA TARAMASI BAŞLADI")
        print("=" * 70)
        print("Ürün:", getattr(product, "name", "-"))

        service = CrossStoreSearchService(
            registry=ScraperRegistry(),
            candidate_limit=4,
            minimum_match_score=0.78,
        )

        result = service.scan_other_stores(
            product
        )

        print()
        print("=" * 70)
        print("ARKA PLAN MAĞAZA TARAMASI TAMAMLANDI")
        print("=" * 70)
        print(
            "Taranan mağaza:",
            result.searched_store_count,
        )
        print(
            "Eklenen teklif:",
            result.saved_offer_count,
        )

        failed_results = [
            item
            for item in result.results
            if not item.success
        ]

        if failed_results:
            print(
                "Başarısız mağaza sayısı:",
                len(failed_results),
            )

            for item in failed_results:
                print(
                    f"- {item.store_name}: "
                    f"{item.message}"
                )

    except Exception as error:
        # Arka plandaki hata kaynak ürünün kaydını etkilemez.
        print()
        print("=" * 70)
        print("ARKA PLAN MAĞAZA TARAMASI HATASI")
        print("=" * 70)
        print(
            type(error).__name__,
            error,
        )


def _start_background_store_scan(
    product: Any,
) -> None:
    """
    Mağaza taramasını beklemeden kuyruğa ekler.
    """
    future = _background_executor.submit(
        _scan_other_stores_in_background,
        product,
    )

    def log_unexpected_future_error(
        completed_future,
    ) -> None:
        try:
            completed_future.result()
        except Exception as error:
            print(
                "Arka plan görevi beklenmeyen hata verdi:",
                type(error).__name__,
                error,
            )

    future.add_done_callback(
        log_unexpected_future_error
    )


def scrape_and_save_product(
    url: str,
    scan_other_stores_enabled: bool = True,
) -> ScanResult:
    """
    URL'den kaynak ürünü tarar ve kaydeder.

    Kaynak ürün başarıyla kaydedildikten sonra diğer mağaza
    taraması arka planda başlatılır. HTTP isteği bu taramanın
    tamamlanmasını beklemez.
    """
    normalized_url = url.strip()

    if not normalized_url:
        return ScanResult(
            success=False,
            message="Ürün bağlantısı boş bırakılamaz.",
        )

    store_code: str | None = None
    store_name: str | None = None

    try:
        store_definition = _registry.detect_store(
            normalized_url
        )

        store_code = store_definition.code
        store_name = store_definition.name

        product = _registry.scrape(
            normalized_url
        )

        if product is None:
            return ScanResult(
                success=False,
                message=(
                    f"{store_name} scraper'ı ürün "
                    "bilgisi döndürmedi."
                ),
                store_code=store_code,
                store_name=store_name,
            )

        save_product(product)

        warnings: list[str] = []

        if scan_other_stores_enabled:
            try:
                _start_background_store_scan(
                    product
                )
            except Exception as background_error:
                warnings.append(
                    "Diğer mağaza taraması arka planda "
                    "başlatılamadı: "
                    f"{type(background_error).__name__}: "
                    f"{background_error}"
                )

        message = (
            f"Ürün {store_name} üzerinden başarıyla "
            "tarandı ve kaydedildi."
        )

        if scan_other_stores_enabled:
            if warnings:
                message += (
                    " Diğer mağaza taraması başlatılamadı."
                )
            else:
                message += (
                    " Diğer mağazalardaki fiyatlar "
                    "arka planda aranıyor."
                )

        return ScanResult(
            success=True,
            message=message,
            store_code=store_code,
            store_name=store_name,
            product=product,
            cross_store_result=None,
            warnings=warnings,
        )

    except ScraperNotImplementedError as error:
        return ScanResult(
            success=False,
            message=str(error),
            store_code=store_code,
            store_name=store_name,
        )

    except UnsupportedStoreError as error:
        return ScanResult(
            success=False,
            message=str(error),
            store_code=store_code,
            store_name=store_name,
        )

    except Exception as error:
        print(
            "Ürün tarama hatası:",
            type(error).__name__,
            error,
        )

        return ScanResult(
            success=False,
            message=(
                "Ürün taranırken hata oluştu: "
                f"{type(error).__name__}: {error}"
            ),
            store_code=store_code,
            store_name=store_name,
        )