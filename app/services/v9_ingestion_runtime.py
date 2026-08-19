from __future__ import annotations

import threading
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.v9_catalog_ingestion_service import run_due_catalog_plans


_scheduler: BackgroundScheduler | None = None
_lock = threading.RLock()


def ensure_v9_ingestion_scheduler() -> BackgroundScheduler:
    """
    V9 katalog besleme kontrolünü bağımsız ve idempotent biçimde başlatır.

    Projenin eski scheduler.py yapısına bağlı değildir. Router uygulama
    başlangıcında import edildiğinde bu fonksiyon bir kez çalışır.
    """
    global _scheduler

    with _lock:
        if _scheduler is not None and _scheduler.running:
            return _scheduler

        scheduler = BackgroundScheduler(
            timezone="Europe/Istanbul",
            daemon=True,
        )
        scheduler.add_job(
            run_due_catalog_plans,
            trigger="interval",
            minutes=5,
            id="v9_catalog_ingestion",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        scheduler.start()
        _scheduler = scheduler
        print(
            "V9 katalog besleme scheduler başlatıldı. "
            "Kontrol aralığı: 5 dakika."
        )
        return scheduler


def v9_ingestion_scheduler_status() -> dict[str, Any]:
    with _lock:
        if _scheduler is None:
            return {
                "started": False,
                "running": False,
                "job_count": 0,
            }
        return {
            "started": True,
            "running": bool(_scheduler.running),
            "job_count": len(_scheduler.get_jobs()),
        }
