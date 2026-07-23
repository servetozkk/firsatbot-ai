from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


_registry = ScraperRegistry()


def get_scraper_registry() -> ScraperRegistry:
    """
    Uygulama genelinde kullanılan ortak
    ScraperRegistry nesnesini döndürür.
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
        return (
            False,
            str(error),
        )

    except Exception as error:
        return (
            False,
            "Ürün bağlantısı doğrulanırken hata oluştu: "
            f"{type(error).__name__}: {error}",
        )


def scrape_and_save_product(
    url: str,
) -> ScanResult:
    """
    URL'den mağazayı tespit eder, ürünü tarar
    ve veritabanına kaydeder.
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

        save_product(
            product
        )

        return ScanResult(
            success=True,
            message=(
                f"Ürün {store_name} üzerinden "
                "başarıyla tarandı ve veritabanına "
                "kaydedildi."
            ),
            store_code=store_code,
            store_name=store_name,
            product=product,
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