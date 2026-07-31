from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any

from app.category_scrapers.registry import CategoryScraperRegistry
from app.models.product import Product
from app.services.product_config_service import add_product
from app.services.product_service import save_product
from app.services.scraper_registry import ScraperRegistry
from app.services.scraper_runtime_config import (
    SCRAPER_REQUEST_DELAY,
    SCRAPER_RETRY_COUNT,
    SCRAPER_WORKERS,
)


@dataclass(slots=True)
class CategoryDiscoveryResult:
    success: bool
    store_code: str
    store_name: str
    category_url: str
    found_count: int = 0
    saved_count: int = 0
    added_to_tracking_count: int = 0
    already_tracked_count: int = 0
    failed_count: int = 0
    visited_page_count: int = 0
    worker_count: int = 1
    list_offer_count: int = 0
    detail_queue_count: int = 0
    skipped_incomplete_count: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CategoryDiscoveryService:
    """Kategori keşfi ve kontrollü paralel ürün detay taraması.

    Liste sayfası önce tek seferde ürün URL'lerini toplar. Ürün detayları daha
    sonra sınırlı worker havuzunda paralel okunur. Veritabanı ve takip listesi
    yazımları ana thread'de seri yapılır; böylece SQLite kilit riskleri azalır.
    """

    def __init__(
        self,
        category_registry: CategoryScraperRegistry | None = None,
        product_registry: ScraperRegistry | None = None,
    ) -> None:
        self.category_registry = category_registry or CategoryScraperRegistry()
        # Geriye dönük uyumluluk için tutulur. Paralel worker'lar kendi registry
        # örneklerini oluşturur; scraper nesneleri thread'ler arasında paylaşılmaz.
        self.product_registry = product_registry or ScraperRegistry()

    @staticmethod
    def _scrape_one(url: str, retry_count: int) -> Any:
        last_error: Exception | None = None
        for attempt in range(retry_count + 1):
            try:
                registry = ScraperRegistry()
                return registry.scrape(url)
            except Exception as error:  # noqa: BLE001 - hata sonuçta raporlanır
                last_error = error
                if attempt < retry_count:
                    time.sleep(1.0 + attempt)
        assert last_error is not None
        raise last_error

    def _save_scraped_product(
        self,
        *,
        product: Any,
        url: str,
        store_name: str,
        result: CategoryDiscoveryResult,
    ) -> None:
        if product is None:
            raise RuntimeError("Ürün scraper'ı veri döndürmedi.")

        save_product(product)
        result.saved_count += 1

        product_name = str(
            getattr(product, "name", None)
            or (product.get("name") if isinstance(product, dict) else "")
            or f"{store_name} Ürünü"
        ).strip()

        add_success, add_message = add_product(
            name=product_name,
            url=url,
            active=True,
        )
        if add_success:
            result.added_to_tracking_count += 1
        elif "zaten" in add_message.lower():
            result.already_tracked_count += 1
        else:
            result.warnings.append(f"{product_name}: {add_message}")

    @staticmethod
    def _product_from_list_offer(link: Any, store_name: str) -> Product:
        return Product(
            name=str(link.name).strip(),
            price=float(link.price),
            old_price=float(link.old_price) if link.old_price is not None else None,
            rating=None,
            review_count=None,
            seller=str(link.seller or store_name),
            url=str(link.url),
            image=link.image,
            brand=link.brand,
            model=None,
            category=None,
            description=None,
            specifications=None,
            stock_status=link.stock_status or "in_stock",
            source_site=link.source_site,
            product_code=link.product_code,
        )

    def _save_list_offers(
        self,
        *,
        links: list[Any],
        store_name: str,
        result: CategoryDiscoveryResult,
    ) -> None:
        for index, link in enumerate(links, start=1):
            print(f"LISTE TEKLİFİ [{index}/{len(links)}] {link.url}")
            try:
                product = self._product_from_list_offer(link, store_name)
                self._save_scraped_product(
                    product=product,
                    url=link.url,
                    store_name=store_name,
                    result=result,
                )
                result.list_offer_count += 1
            except Exception as error:  # noqa: BLE001
                result.failed_count += 1
                result.errors.append(
                    f"{link.url}: {type(error).__name__}: {error}"
                )

    def scan_and_save(
        self,
        category_url: str,
        limit: int = 100,
        max_pages: int = 10,
    ) -> CategoryDiscoveryResult:
        category_scraper = self.category_registry.get_scraper(category_url)
        link_result = category_scraper.collect_product_links(
            category_url=category_url,
            limit=limit,
            max_pages=max_pages,
        )

        worker_count = min(SCRAPER_WORKERS, max(1, len(link_result.links)))
        result = CategoryDiscoveryResult(
            success=True,
            store_code=link_result.store_code,
            store_name=link_result.store_name,
            category_url=link_result.category_url,
            found_count=link_result.found_count,
            visited_page_count=link_result.visited_page_count,
            worker_count=worker_count,
            warnings=list(link_result.warnings),
        )

        if not link_result.links:
            return result

        # Hepsiburada V3: kategori kartındaki ürün özeti doğrudan teklif olarak
        # kaydedilir. Detay sayfaları güvenlik doğrulamasına takıldığı için açılmaz.
        if link_result.store_code == "hepsiburada":
            list_links = [link for link in link_result.links if link.has_list_offer]
            incomplete_links = [link for link in link_result.links if not link.has_list_offer]
            result.worker_count = 0
            result.detail_queue_count = 0
            result.skipped_incomplete_count = len(incomplete_links)
            if incomplete_links:
                result.warnings.append(
                    f"{len(incomplete_links)} ürün kartında fiyat/ad bulunamadığı için "
                    "detay sayfası açılmadan atlandı."
                )
            print()
            print("=" * 70)
            print(
                f"HEPSİBURADA LİSTE MODU: {len(list_links)} teklif doğrudan "
                "kategori kartından kaydedilecek"
            )
            self._save_list_offers(
                links=list_links,
                store_name=link_result.store_name,
                result=result,
            )
            if result.found_count > 0 and result.saved_count == 0:
                result.success = False
            return result

        result.detail_queue_count = len(link_result.links)

        print()
        print("=" * 70)
        print(
            f"DETAY KUYRUĞU: {len(link_result.links)} ürün, "
            f"{worker_count} paralel worker"
        )

        future_map: dict[Future[Any], tuple[int, Any]] = {}
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix=f"{link_result.store_code}-detail",
        ) as executor:
            for index, link in enumerate(link_result.links, start=1):
                future = executor.submit(
                    self._scrape_one,
                    link.url,
                    SCRAPER_RETRY_COUNT,
                )
                future_map[future] = (index, link)
                if SCRAPER_REQUEST_DELAY > 0:
                    time.sleep(SCRAPER_REQUEST_DELAY)

            completed = 0
            for future in as_completed(future_map):
                completed += 1
                index, link = future_map[future]
                print()
                print("-" * 70)
                print(
                    f"DETAY SONUCU [{completed}/{len(future_map)}] "
                    f"(kuyruk sırası {index}) {link.source_site}"
                )
                print(link.url)

                try:
                    product = future.result()
                    self._save_scraped_product(
                        product=product,
                        url=link.url,
                        store_name=link_result.store_name,
                        result=result,
                    )
                except Exception as error:  # noqa: BLE001
                    result.failed_count += 1
                    result.errors.append(
                        f"{link.url}: {type(error).__name__}: {error}"
                    )
                    print(
                        "Kategori ürün tarama hatası:",
                        type(error).__name__,
                        error,
                    )

        if result.found_count > 0 and result.saved_count == 0:
            result.success = False

        return result
