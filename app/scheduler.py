from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Any

from app.services.category_service import get_active_categories
from app.services.catalog_scan_plan_service import get_active_catalog_plans
from app.core.config import settings
from app.services.category_discovery_service import CategoryDiscoveryService
from app.services.workload_priority_v23612 import user_deep_priority_active_v23612

_discovery_service = CategoryDiscoveryService()


DEFAULT_SCAN_INTERVAL_MINUTES = 15

_scheduler_task: asyncio.Task[Any] | None = None
_stop_event: asyncio.Event | None = None


def get_scan_interval_seconds() -> int:
    """
    Kategori tarama süresini ortam değişkeninden alır.

    Örnek:
    CATEGORY_SCAN_INTERVAL_MINUTES=15
    """

    raw_value = os.getenv(
        "CATEGORY_SCAN_INTERVAL_MINUTES",
        str(DEFAULT_SCAN_INTERVAL_MINUTES),
    )

    try:
        minutes = int(raw_value)

    except ValueError:
        print(
            "Geçersiz CATEGORY_SCAN_INTERVAL_MINUTES değeri:",
            raw_value,
        )

        minutes = DEFAULT_SCAN_INTERVAL_MINUTES

    if minutes < 1:
        minutes = 1

    return minutes * 60



def scan_all_active_catalog_plans() -> dict[str, Any]:
    plans=get_active_catalog_plans(); result={"catalog_count":len(plans),"store_count":0,"found_count":0,"saved_count":0,"failed_store_count":0,"results":[]}
    for plan in plans:
        if user_deep_priority_active_v23612():
            print("V23.61.4 CATEGORY PLAN YIELD: user-ingestion-priority-active.")
            break
        for source in [s for s in plan.get("sources",[]) if s.get("active",True)]:
            if user_deep_priority_active_v23612():
                print("V23.61.4 CATEGORY SOURCE YIELD: user-ingestion-priority-active.")
                break
            result["store_count"]+=1
            try:
                row=_discovery_service.scan_and_save(category_url=source["url"],limit=plan["limit"]).to_dict()
                result["found_count"]+=int(row.get("found_count",0));result["saved_count"]+=int(row.get("saved_count",0));result["results"].append({"plan":plan["name"],"store":source["store_name"],"success":True,**row})
            except Exception as error:
                result["failed_store_count"]+=1;result["results"].append({"plan":plan["name"],"store":source["store_name"],"success":False,"error":str(error)})
    return result

def scan_scheduled_catalogs() -> dict[str, Any]:
    return scan_all_active_catalog_plans() if get_active_catalog_plans() else scan_all_active_categories()

def scan_all_active_categories() -> dict[str, Any]:
    """
    Tüm aktif kategorileri sırayla tarar.

    Bu fonksiyon senkron çalışır. Scheduler içinde
    asyncio.to_thread ile ayrı iş parçacığında çalıştırılır.
    """

    categories = get_active_categories()

    result: dict[str, Any] = {
        "category_count": len(categories),
        "successful_category_count": 0,
        "failed_category_count": 0,
        "found_count": 0,
        "saved_count": 0,
        "added_to_tracking_count": 0,
        "already_tracked_count": 0,
        "failed_product_count": 0,
        "results": [],
    }

    if not categories:
        print("Scheduler: Taranacak aktif kategori bulunamadı.")
        return result

    print(
        f"Scheduler: {len(categories)} aktif kategori taranıyor..."
    )

    for category in categories:
        if user_deep_priority_active_v23612():
            print("V23.61.4 CATEGORY SCHEDULER YIELD: user-ingestion-priority-active.")
            break
        category_name = category.get(
            "name",
            "İsimsiz kategori",
        )

        category_url = category.get(
            "url",
            "",
        )

        category_limit = category.get(
            "limit",
            10,
        )

        try:
            scan_result = _discovery_service.scan_and_save(
                category_url=category_url,
                limit=category_limit,
            ).to_dict()

            result["successful_category_count"] += 1
            result["found_count"] += scan_result.get(
                "found_count",
                0,
            )
            result["saved_count"] += scan_result.get(
                "saved_count",
                0,
            )
            result["added_to_tracking_count"] += (
                scan_result.get(
                    "added_to_tracking_count",
                    0,
                )
            )
            result["already_tracked_count"] += (
                scan_result.get(
                    "already_tracked_count",
                    0,
                )
            )
            result["failed_product_count"] += (
                scan_result.get(
                    "failed_count",
                    0,
                )
            )

            result["results"].append({
                "category_id": category.get("id"),
                "category_name": category_name,
                "success": True,
                **scan_result,
            })

            print(
                f'Scheduler: "{category_name}" tamamlandı. '
                f'{scan_result.get("found_count", 0)} ürün bulundu.'
            )

        except Exception as error:
            result["failed_category_count"] += 1

            result["results"].append({
                "category_id": category.get("id"),
                "category_name": category_name,
                "success": False,
                "error": str(error),
            })

            print(
                f'Scheduler: "{category_name}" taranamadı:',
                error,
            )

    print(
        "Scheduler taraması tamamlandı. "
        f'Başarılı kategori: '
        f'{result["successful_category_count"]}, '
        f'Hatalı kategori: '
        f'{result["failed_category_count"]}, '
        f'Bulunan ürün: {result["found_count"]}, '
        f'Kaydedilen ürün: {result["saved_count"]}.'
    )

    return result


async def scheduler_loop() -> None:
    """
    Belirlenen süre boyunca bekler ve ardından
    aktif kategorileri otomatik olarak tarar.
    """

    global _stop_event

    interval_seconds = get_scan_interval_seconds()
    interval_minutes = interval_seconds // 60

    print(
        f"Kategori scheduler başlatıldı. "
        f"Tarama aralığı: {interval_minutes} dakika."
    )

    _stop_event = asyncio.Event()

    while not _stop_event.is_set():
        try:
            await asyncio.wait_for(
                _stop_event.wait(),
                timeout=interval_seconds,
            )

        except asyncio.TimeoutError:
            pass

        if _stop_event.is_set():
            break

        started_at = datetime.now()

        print(
            "Otomatik kategori taraması başladı:",
            started_at.strftime("%d.%m.%Y %H:%M:%S"),
        )

        try:
            await asyncio.to_thread(
                scan_scheduled_catalogs
            )

        except asyncio.CancelledError:
            raise

        except Exception as error:
            print(
                "Scheduler genel tarama hatası:",
                error,
            )

    print("Kategori scheduler durduruldu.")


async def start_scheduler() -> None:
    """
    Scheduler görevini başlatır.
    Birden fazla kez başlatılmasını engeller.
    """

    global _scheduler_task

    if not settings.enable_scheduler:
        print("Kategori scheduler devre dışı.")
        return

    if (
        _scheduler_task is not None
        and not _scheduler_task.done()
    ):
        print("Kategori scheduler zaten çalışıyor.")
        return

    _scheduler_task = asyncio.create_task(
        scheduler_loop(),
        name="category-scheduler",
    )


async def stop_scheduler() -> None:
    """
    Uygulama kapanırken scheduler görevini güvenli şekilde durdurur.
    """

    global _scheduler_task
    global _stop_event

    if _stop_event is not None:
        _stop_event.set()

    if _scheduler_task is None:
        return

    try:
        await asyncio.wait_for(
            _scheduler_task,
            timeout=5,
        )

    except asyncio.TimeoutError:
        _scheduler_task.cancel()

        try:
            await _scheduler_task

        except asyncio.CancelledError:
            pass

    finally:
        _scheduler_task = None
        _stop_event = None
