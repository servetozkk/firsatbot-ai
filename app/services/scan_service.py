from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any
from threading import RLock
from uuid import uuid4
from datetime import datetime
from urllib.parse import urlsplit
import re

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
    cross_store_task_id: str | None = None


_registry = ScraperRegistry()

# Aynı anda en fazla iki ayrı ürün için mağaza taraması çalışır.
# Böylece bilgisayar onlarca Chrome penceresiyle aşırı yüklenmez.
_background_executor = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="cross-store-scan",
)


_cross_store_tasks: dict[str, dict[str, Any]] = {}
_cross_store_tasks_lock = RLock()


def _task_update(task_id: str, **changes: Any) -> None:
    with _cross_store_tasks_lock:
        task = _cross_store_tasks.get(task_id)
        if task is not None:
            task.update(changes)
            task["updated_at"] = datetime.utcnow().isoformat()


def get_cross_store_scan_task(task_id: str) -> dict[str, Any] | None:
    with _cross_store_tasks_lock:
        task = _cross_store_tasks.get(str(task_id or ""))
        return dict(task) if task else None


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




def classify_store_url(url: str) -> str:
    """Bağlantıyı ürün, kategori/arama veya bilinmeyen olarak sınıflandırır.

    Ürün ekleme ekranına kategori/arama URL'si yapıştırıldığında scraper'ın
    arama sonuç sayfasını ürün gibi işlemesini engeller.
    """
    value = str(url or "").strip()
    if not value:
        return "unknown"
    try:
        parts = urlsplit(value)
    except Exception:
        return "unknown"

    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.lower().rstrip("/")
    query = parts.query.lower()

    # Trendyol ürün URL'leri tipik olarak -p-<id> ile biter. /sr ve -c<id>
    # bağlantıları arama/kategori sayfasıdır.
    if "trendyol.com" in host:
        if re.search(r"-p-\d+(?:$|[/?])", path + "/"):
            return "product"
        if path == "/sr" or "/sr/" in path or re.search(r"-c\d+(?:$|[/?])", path + "/") or "wc=" in query:
            return "category"

    if "hepsiburada.com" in host:
        if re.search(r"-p-[a-z0-9]+(?:$|[/?])", path + "/"):
            return "product"
        if "/ara" in path or "/kategori/" in path:
            return "category"

    if "n11.com" in host:
        if "/urun/" in path:
            return "product"
        if "/arama" in path or "/kategori/" in path:
            return "category"


    if "pttavm.com" in host:
        if re.search(r"-p-\d+(?:$|[/?])", path + "/"):
            return "product"
        if "/arama" in path or "/kategori/" in path or "/magaza/" in path:
            return "category"

    if "beymen.com" in host:
        if re.search(r"/tr/p_[^/]+_\d+(?:$|[/?])", path + "/"):
            return "product"
        if "/cep-telefonu-" in path or "/telefon-" in path or "/search" in path or "/arama" in path:
            return "category"

    if "teknosa.com" in host:
        if re.search(r"-p-\d+(?:$|[/?])", path + "/"):
            return "product"
        if re.search(r"-c-\d+(?:$|[/?])", path + "/"):
            return "category"

    if "mediamarkt.com.tr" in host:
        if "/product/" in path or "/product_" in path or "/tr/product/" in path:
            return "product"
        if "/category/" in path or "/search" in path:
            return "category"

    if "vatanbilgisayar.com" in host:
        if path.endswith(".html") and not any(token in path for token in ("/arama", "/kategori", "/product-list")):
            return "product"
        if "/arama" in path or "/kategori" in path:
            return "category"

    if "pazarama.com" in host:
        if re.search(r"-p-(?:\d{8,}|[a-z0-9-]{10,})(?:$|[/?])", path + "/"):
            return "product"
        if "/arama" in path or "/kategori" in path:
            return "category"

    if "amazon.com.tr" in host:
        if "/dp/" in path or "/gp/product/" in path:
            return "product"
        if "/s" == path or path.startswith("/s/") or "k=" in query:
            return "category"

    # Genel ürün işaretleri. Kesin kategori işaretleri önceliklidir.
    if any(token in path for token in ("/search", "/arama", "/category", "/kategori")):
        return "category"
    if any(token in path for token in ("/product/", "/urun/", "/dp/")):
        return "product"
    return "unknown"

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
        url_kind = classify_store_url(normalized_url)
        if url_kind == "category":
            return (
                False,
                "Bu bağlantı bir ürün değil, kategori veya arama sayfası. "
                "Kategori taraması için Admin > Kategoriler bölümünü kullanın.",
            )

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
    task_id: str,
    product: Any,
) -> None:
    try:
        _task_update(
            task_id,
            status="running",
            progress=10,
            message="Ürün kimliği oluşturuldu; diğer mağazalarda aranıyor.",
        )

        service = CrossStoreSearchService(
            registry=ScraperRegistry(),
            candidate_limit=6,
            minimum_match_score=0.78,
            parallel_workers=2,
        )
        result = service.scan_other_stores(product)

        serialized_results = [
            {
                "store_code": item.store_code,
                "store_name": item.store_name,
                "success": item.success,
                "message": item.message,
                "product_url": item.product_url,
                "match_score": item.match_score,
            }
            for item in result.results
        ]
        _task_update(
            task_id,
            status="completed",
            progress=100,
            message=(
                f"{result.searched_store_count} mağaza tarandı, "
                f"{result.saved_offer_count} eşleşen teklif kaydedildi."
            ),
            searched_store_count=result.searched_store_count,
            saved_offer_count=result.saved_offer_count,
            results=serialized_results,
            completed_at=datetime.utcnow().isoformat(),
        )
    except Exception as error:
        _task_update(
            task_id,
            status="failed",
            progress=100,
            message=f"Çok mağazalı tarama hatası: {type(error).__name__}: {error}",
            error=f"{type(error).__name__}: {error}",
            completed_at=datetime.utcnow().isoformat(),
        )


def _start_background_store_scan(product: Any) -> str:
    task_id = str(uuid4())
    with _cross_store_tasks_lock:
        _cross_store_tasks[task_id] = {
            "id": task_id,
            "status": "queued",
            "progress": 0,
            "message": "Çok mağazalı tarama kuyruğa alındı.",
            "source_product_name": getattr(product, "name", ""),
            "searched_store_count": 0,
            "saved_offer_count": 0,
            "results": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    future = _background_executor.submit(
        _scan_other_stores_in_background,
        task_id,
        product,
    )

    def log_unexpected_future_error(completed_future) -> None:
        try:
            completed_future.result()
        except Exception as error:
            _task_update(
                task_id,
                status="failed",
                progress=100,
                message=f"Arka plan görevi hata verdi: {type(error).__name__}: {error}",
            )

    future.add_done_callback(log_unexpected_future_error)
    return task_id


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
        url_kind = classify_store_url(normalized_url)
        if url_kind == "category":
            return ScanResult(
                success=False,
                message=(
                    "Kategori veya arama bağlantısı ürün olarak eklenemez. "
                    "Admin > Kategoriler bölümünden tarama başlatın."
                ),
            )

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
        cross_store_task_id: str | None = None

        if scan_other_stores_enabled:
            try:
                cross_store_task_id = _start_background_store_scan(
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
            cross_store_task_id=cross_store_task_id,
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