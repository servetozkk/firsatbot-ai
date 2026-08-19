from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.bulk_catalog_service import run_bulk_plan


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class BulkTask:
    id: str
    plan_id: str
    status: str = "queued"
    progress: int = 0
    current_store: str = ""
    message: str = "Toplu katalog görevi sıraya alındı."
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BulkCatalogManager:
    def __init__(self) -> None:
        self._tasks: dict[str, BulkTask] = {}
        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bulk-catalog")

    def start(self, plan_id: str) -> dict[str, Any]:
        task = BulkTask(id=str(uuid4()), plan_id=str(plan_id))
        with self._lock:
            self._tasks[task.id] = task
        self._pool.submit(self._run, task.id)
        return task.to_dict()

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            task = self._tasks.get(str(task_id))
            return task.to_dict() if task else None

    def _update(self, task_id: str, **values: Any) -> None:
        with self._lock:
            task = self._tasks[task_id]
            for key, value in values.items():
                setattr(task, key, value)

    def _run(self, task_id: str) -> None:
        task = self._tasks[task_id]
        self._update(task_id, status="running", progress=1, started_at=_now(), message="Mağaza katalogları bağımsız toplanıyor")
        try:
            result = run_bulk_plan(
                task.plan_id,
                progress=lambda pct, store, msg: self._update(task_id, progress=pct, current_store=store, message=msg),
            ).to_dict()
            status = "completed" if not result["failed_store_count"] else "completed_with_errors"
            self._update(task_id, status=status, progress=100, finished_at=_now(), result=result, message="Toplu katalog taraması tamamlandı")
        except Exception as exc:  # noqa: BLE001
            self._update(task_id, status="failed", progress=100, finished_at=_now(), error=f"{type(exc).__name__}: {exc}", message="Toplu katalog görevi başarısız")


bulk_catalog_manager = BulkCatalogManager()
