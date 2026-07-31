from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.services.category_discovery_service import CategoryDiscoveryService
from app.services.category_service import get_active_categories, get_category_by_id


HISTORY_PATH = Path("data/category_scan_history.json")
_HISTORY_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass(slots=True)
class ScanTask:
    id: str
    kind: str
    status: str = "queued"
    progress: int = 0
    message: str = "Tarama sıraya alındı."
    category_id: str | None = None
    category_name: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    logs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CategoryScanManager:
    def __init__(self) -> None:
        self._tasks: dict[str, ScanTask] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="category-scan")

    def _set(self, task_id: str, **changes: Any) -> None:
        with self._lock:
            task = self._tasks[task_id]
            for key, value in changes.items():
                setattr(task, key, value)

    def _log(self, task_id: str, text: str) -> None:
        with self._lock:
            task = self._tasks[task_id]
            task.logs.append(text)
            task.logs = task.logs[-100:]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.to_dict() if task else None

    def list_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            tasks = list(self._tasks.values())[-limit:]
            return [task.to_dict() for task in reversed(tasks)]

    def start_category(self, category_id: str) -> dict[str, Any]:
        category = get_category_by_id(category_id)
        if category is None:
            raise ValueError("Kategori bulunamadı.")

        task = ScanTask(
            id=str(uuid4()),
            kind="single",
            category_id=category_id,
            category_name=category["name"],
        )
        with self._lock:
            self._tasks[task.id] = task
        self._executor.submit(self._run_single, task.id, category)
        return task.to_dict()

    def start_all(self) -> dict[str, Any]:
        categories = get_active_categories()
        if not categories:
            raise ValueError("Taranacak aktif kategori bulunamadı.")

        task = ScanTask(id=str(uuid4()), kind="all", category_name="Tüm aktif kategoriler")
        with self._lock:
            self._tasks[task.id] = task
        self._executor.submit(self._run_all, task.id, categories)
        return task.to_dict()

    def _run_single(self, task_id: str, category: dict[str, Any]) -> None:
        self._set(
            task_id,
            status="running",
            progress=10,
            started_at=_now_iso(),
            message=f"{category['name']} taranıyor…",
        )
        self._log(task_id, f"Kategori başlatıldı: {category['name']}")
        try:
            service = CategoryDiscoveryService()
            self._set(task_id, progress=25, message="Ürün bağlantıları toplanıyor…")
            result = service.scan_and_save(
                category_url=category["url"],
                limit=category["limit"],
            ).to_dict()
            self._set(
                task_id,
                status="completed" if result.get("success") else "failed",
                progress=100,
                finished_at=_now_iso(),
                result=result,
                error=None if result.get("success") else "Bazı veya tüm ürünler kaydedilemedi.",
                message=(
                    f"{result.get('found_count', 0)} ürün bulundu, "
                    f"{result.get('saved_count', 0)} ürün kaydedildi."
                ),
            )
            self._log(task_id, "Kategori taraması tamamlandı.")
            self._append_history(self.get_task(task_id) or {})
        except Exception as error:
            self._set(
                task_id,
                status="failed",
                progress=100,
                finished_at=_now_iso(),
                error=f"{type(error).__name__}: {error}",
                message="Kategori taraması başarısız oldu.",
            )
            self._log(task_id, f"Hata: {type(error).__name__}: {error}")
            self._append_history(self.get_task(task_id) or {})

    def _run_all(self, task_id: str, categories: list[dict[str, Any]]) -> None:
        self._set(
            task_id,
            status="running",
            progress=1,
            started_at=_now_iso(),
            message=f"{len(categories)} kategori taranacak.",
        )
        results: list[dict[str, Any]] = []
        service = CategoryDiscoveryService()

        for index, category in enumerate(categories, start=1):
            progress = max(1, int(((index - 1) / len(categories)) * 100))
            self._set(
                task_id,
                progress=progress,
                message=f"{category['name']} taranıyor ({index}/{len(categories)})…",
            )
            self._log(task_id, f"[{index}/{len(categories)}] {category['name']}")
            try:
                result = service.scan_and_save(
                    category_url=category["url"],
                    limit=category["limit"],
                ).to_dict()
                results.append({"category": category, "result": result})
            except Exception as error:
                results.append({
                    "category": category,
                    "error": f"{type(error).__name__}: {error}",
                })

        found = sum(int(item.get("result", {}).get("found_count", 0)) for item in results)
        saved = sum(int(item.get("result", {}).get("saved_count", 0)) for item in results)
        failed = sum(1 for item in results if item.get("error") or not item.get("result", {}).get("success", False))
        aggregate = {
            "success": failed == 0,
            "category_count": len(categories),
            "failed_category_count": failed,
            "found_count": found,
            "saved_count": saved,
            "results": results,
        }
        self._set(
            task_id,
            status="completed" if failed == 0 else "failed",
            progress=100,
            finished_at=_now_iso(),
            result=aggregate,
            error=None if failed == 0 else f"{failed} kategoride hata oluştu.",
            message=f"{found} ürün bulundu, {saved} ürün kaydedildi.",
        )
        self._append_history(self.get_task(task_id) or {})

    @staticmethod
    def _append_history(task: dict[str, Any]) -> None:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _HISTORY_LOCK:
            try:
                history = json.loads(HISTORY_PATH.read_text(encoding="utf-8")) if HISTORY_PATH.exists() else []
                if not isinstance(history, list):
                    history = []
            except (OSError, json.JSONDecodeError):
                history = []
            history.append(task)
            HISTORY_PATH.write_text(
                json.dumps(history[-200:], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    @staticmethod
    def get_history(limit: int = 20) -> list[dict[str, Any]]:
        if not HISTORY_PATH.exists():
            return []
        with _HISTORY_LOCK:
            try:
                history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return []
        if not isinstance(history, list):
            return []
        return list(reversed(history[-limit:]))


category_scan_manager = CategoryScanManager()
