from __future__ import annotations

import asyncio
import os
from contextlib import suppress

from app.database.database import create_db
from app.services.product_config_service import (
    get_products,
)
from app.services.scan_service import (
    scrape_and_save_product,
)


DEFAULT_SCAN_INTERVAL_MINUTES = 30

_scheduler_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


def _get_scan_interval_seconds() -> int:
    """
    Tarama aralığını .env dosyasından dakika
    olarak okur ve saniyeye çevirir.
    """
    raw_value = os.getenv(
        "SCAN_INTERVAL_MINUTES",
        str(DEFAULT_SCAN_INTERVAL_MINUTES),
    )

    try:
        interval_minutes = int(
            raw_value
        )

        if interval_minutes < 1:
            raise ValueError

    except (TypeError, ValueError):
        print(
            "Geçersiz SCAN_INTERVAL_MINUTES değeri. "
            f"Varsayılan {DEFAULT_SCAN_INTERVAL_MINUTES} "
            "dakika kullanılacak."
        )

        interval_minutes = (
            DEFAULT_SCAN_INTERVAL_MINUTES
        )

    return interval_minutes * 60


def scan_active_products() -> dict[str, int]:
    """
    Takip listesindeki aktif ürünleri
    ScraperRegistry üzerinden tarar.
    """
    products = get_products()

    active_products = [
        product
        for product in products
        if bool(product.get("active", False))
        and str(
            product.get("url", "")
        ).strip()
    ]

    stats = {
        "total": len(active_products),
        "successful": 0,
        "failed": 0,
    }

    print()
    print("=" * 70)
    print(
        "ÜRÜN TARAMASI BAŞLADI"
    )
    print(
        f"Aktif ürün sayısı: {stats['total']}"
    )
    print("=" * 70)

    if not active_products:
        print(
            "Taranacak aktif ürün bulunamadı."
        )

        return stats

    for index, configured_product in enumerate(
        active_products,
        start=1,
    ):
        product_url = str(
            configured_product.get("url", "")
        ).strip()

        product_name = str(
            configured_product.get(
                "name",
                product_url,
            )
        ).strip()

        print()
        print(
            f"[{index}/{stats['total']}] "
            f"{product_name}"
        )
        print(
            f"URL: {product_url}"
        )

        try:
            result = scrape_and_save_product(
                product_url
            )

            if result.success:
                stats["successful"] += 1

                print(
                    f"[BAŞARILI] {result.message}"
                )

            else:
                stats["failed"] += 1

                print(
                    f"[BAŞARISIZ] {result.message}"
                )

        except Exception as error:
            stats["failed"] += 1

            print(
                "[BEKLENMEYEN HATA] "
                f"{type(error).__name__}: {error}"
            )

    print()
    print("=" * 70)
    print(
        "ÜRÜN TARAMASI TAMAMLANDI"
    )
    print(
        f"Toplam: {stats['total']}"
    )
    print(
        f"Başarılı: {stats['successful']}"
    )
    print(
        f"Başarısız: {stats['failed']}"
    )
    print("=" * 70)

    return stats


async def _scheduler_loop() -> None:
    """
    Scheduler'ın arka planda çalışan ana döngüsü.
    """
    if _stop_event is None:
        raise RuntimeError(
            "Scheduler durdurma sinyali "
            "oluşturulmadı."
        )

    interval_seconds = (
        _get_scan_interval_seconds()
    )

    interval_minutes = (
        interval_seconds // 60
    )

    while not _stop_event.is_set():
        try:
            await asyncio.to_thread(
                scan_active_products
            )

        except asyncio.CancelledError:
            raise

        except Exception as error:
            print(
                "Scheduler tarama hatası: "
                f"{type(error).__name__}: {error}"
            )

        print(
            "Sonraki tarama "
            f"{interval_minutes} dakika sonra."
        )

        try:
            await asyncio.wait_for(
                _stop_event.wait(),
                timeout=interval_seconds,
            )

        except asyncio.TimeoutError:
            continue


async def start_scheduler() -> None:
    """
    FastAPI açılırken scheduler görevini başlatır.
    """
    global _scheduler_task
    global _stop_event

    if (
        _scheduler_task is not None
        and not _scheduler_task.done()
    ):
        print(
            "Scheduler zaten çalışıyor."
        )
        return

    create_db()

    _stop_event = asyncio.Event()

    _scheduler_task = asyncio.create_task(
        _scheduler_loop(),
        name="product-scan-scheduler",
    )

    interval_minutes = (
        _get_scan_interval_seconds() // 60
    )

    print(
        "Scheduler başlatıldı. "
        f"Tarama aralığı: {interval_minutes} dakika."
    )


async def stop_scheduler() -> None:
    """
    FastAPI kapanırken scheduler görevini
    güvenli şekilde durdurur.
    """
    global _scheduler_task
    global _stop_event

    if _scheduler_task is None:
        return

    if _stop_event is not None:
        _stop_event.set()

    _scheduler_task.cancel()

    with suppress(
        asyncio.CancelledError
    ):
        await _scheduler_task

    _scheduler_task = None
    _stop_event = None

    print(
        "Scheduler durduruldu."
    )