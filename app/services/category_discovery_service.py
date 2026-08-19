from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from app.category_scrapers.registry import CategoryScraperRegistry
from app.models.product import Product
from app.services.product_config_service import add_product
from app.services.product_service import save_product
from app.services.scraper_registry import ScraperRegistry
from app.services.cross_store_search_service import CrossStoreSearchService
from app.services.product_identity_service import ProductIdentityService
from app.services.scraper_resilience_service import resilient_call, store_code_from_url
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
    reconciled_product_count: int = 0
    cross_store_saved_offer_count: int = 0
    reconciliation_errors: list[str] = field(default_factory=list)
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
        def operation() -> Any:
            return ScraperRegistry().scrape(url)
        return resilient_call(store_code=store_code_from_url(url),url=url,operation=operation,requested_retries=retry_count,context="category_product_detail")

    def _save_scraped_product(
        self,
        *,
        product: Any,
        url: str,
        store_name: str,
        result: CategoryDiscoveryResult,
        collected_products: list[Any] | None = None,
    ) -> Any:
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

        if collected_products is not None:
            collected_products.append(product)

        return product

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
        collected_products: list[Any] | None = None,
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
                    collected_products=collected_products,
                )
                result.list_offer_count += 1
            except Exception as error:  # noqa: BLE001
                result.failed_count += 1
                result.errors.append(
                    f"{link.url}: {type(error).__name__}: {error}"
                )

    @staticmethod
    def _unique_reconciliation_products(
        products: list[Any],
        maximum: int,
    ) -> list[Any]:
        unique: list[Any] = []
        seen: set[str] = set()

        for product in products:
            try:
                identity = ProductIdentityService.explain(product)
                key = str(identity.get("identity_key") or "").strip()
            except Exception:
                key = ""

            if not key:
                key = str(getattr(product, "name", "") or "").casefold().strip()

            if not key or key in seen:
                continue

            seen.add(key)
            unique.append(product)

            if len(unique) >= maximum:
                break

        return unique

    def _reconcile_across_stores(
        self,
        *,
        products: list[Any],
        result: CategoryDiscoveryResult,
        maximum_products: int,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> None:
        candidates = self._unique_reconciliation_products(
            products,
            maximum=max(0, maximum_products),
        )
        if not candidates:
            return

        print()
        print("=" * 70)
        print("KATALOG UZLAŞTIRMA MOTORU")
        print("=" * 70)
        print("Hedefli aranacak benzersiz ürün:", len(candidates))

        def report_store_progress(
            product_index: int,
            store_current: int,
            store_total: int,
            message: str,
        ) -> None:
            if progress_callback is None:
                return
            product_fraction = (
                (product_index - 1) + (store_current / max(1, store_total))
            ) / max(1, len(candidates))
            progress_callback(
                "reconciliation",
                min(1.0, max(0.0, product_fraction)),
                f"Mağazalar arası eşleştirme {product_index}/{len(candidates)} — {message}",
            )

        for index, product in enumerate(candidates, start=1):
            print()
            print(
                f"UZLAŞTIRMA [{index}/{len(candidates)}]: "
                f"{getattr(product, 'name', '')}"
            )
            service = CrossStoreSearchService(
                registry=ScraperRegistry(),
                candidate_limit=3,
                minimum_match_score=0.82,
                parallel_workers=3,
                max_store_count=5,
                fast_mode=True,
                progress_callback=lambda current, total, message, idx=index: (
                    report_store_progress(idx, current, total, message)
                ),
            )
            if progress_callback is not None:
                progress_callback(
                    "reconciliation",
                    (index - 1) / max(1, len(candidates)),
                    f"Mağazalar arası eşleştirme {index}/{len(candidates)} başladı",
                )
            try:
                scan = service.scan_other_stores(product)
                result.reconciled_product_count += 1
                result.cross_store_saved_offer_count += int(
                    scan.saved_offer_count or 0
                )
                for store_result in scan.results:
                    if not store_result.success:
                        result.reconciliation_errors.append(
                            f"{getattr(product, 'name', '')} / "
                            f"{store_result.store_name}: "
                            f"{store_result.message}"
                        )
            except Exception as error:
                result.reconciliation_errors.append(
                    f"{getattr(product, 'name', '')}: "
                    f"{type(error).__name__}: {error}"
                )

    def scan_and_save(
        self,
        category_url: str,
        limit: int = 100,
        max_pages: int = 10,
        reconcile_across_stores: bool = True,
        reconciliation_product_limit: int = 10,
        progress_callback: Callable[[str, float, str], None] | None = None,
    ) -> CategoryDiscoveryResult:
        if progress_callback is not None:
            progress_callback("category", 0.0, "Kategori ürün bağlantıları toplanıyor")
        category_scraper = self.category_registry.get_scraper(category_url)
        link_result = category_scraper.collect_product_links(
            category_url=category_url,
            limit=limit,
            max_pages=max_pages,
        )
        if progress_callback is not None:
            progress_callback(
                "category",
                1.0,
                f"{link_result.found_count} ürün bağlantısı bulundu",
            )

        worker_count = min(SCRAPER_WORKERS, max(1, len(link_result.links)))
        # N11 kalıcı Chrome profilini kullanır. Aynı profil birden fazla
        # process/context tarafından eş zamanlı açılırsa TargetClosedError oluşur.
        if link_result.store_code == "n11":
            worker_count = 1
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

        collected_products: list[Any] = []

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
                collected_products=collected_products,
            )
            if reconcile_across_stores:
                self._reconcile_across_stores(
                    products=collected_products,
                    result=result,
                    maximum_products=reconciliation_product_limit,
                    progress_callback=progress_callback,
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
                if progress_callback is not None:
                    progress_callback(
                        "detail",
                        completed / max(1, len(future_map)),
                        f"Ürün detayları işleniyor {completed}/{len(future_map)}",
                    )
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
                        collected_products=collected_products,
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

        if reconcile_across_stores:
            self._reconcile_across_stores(
                products=collected_products,
                result=result,
                maximum_products=reconciliation_product_limit,
            )

        if result.found_count > 0 and result.saved_count == 0:
            result.success = False

        return result
