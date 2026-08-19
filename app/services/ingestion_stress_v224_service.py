from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import RLock
from time import sleep
from typing import Any
from uuid import uuid4

from app.services.production_ingestion_v220_service import (
    get_ingestion_task,
    start_production_ingestion,
)

ENGINE = "FIRSATAI_CONTROLLED_INGESTION_STRESS_TEST"
VERSION = "22.4.0"
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="v224-stress")
_runs: dict[str, dict[str, Any]] = {}
_lock = RLock()


def _update(run_id: str, **changes: Any) -> None:
    with _lock:
        row = _runs.get(run_id)
        if row is not None:
            row.update(changes)
            row["updated_at"] = datetime.utcnow().isoformat()


def get_stress_run(run_id: str) -> dict[str, Any] | None:
    with _lock:
        row = _runs.get(str(run_id or ""))
        return dict(row) if row else None


def _wait_task(task_id: str, timeout_seconds: int) -> dict[str, Any]:
    waited = 0.0
    while waited < timeout_seconds:
        row = get_ingestion_task(task_id)
        if row and str(row.get("status")) in ("COMPLETED", "FAILED"):
            return row
        sleep(1.0)
        waited += 1.0
    return {
        "task_id": task_id,
        "status": "TIMEOUT",
        "error": f"Stress runner {timeout_seconds} saniye içinde ingestion tamamlanmasını göremedi.",
    }


def _run(run_id: str, urls: list[str], candidate_limit: int, parallel_workers: int, per_product_timeout_seconds: int) -> None:
    _update(run_id, status="RUNNING", started_at=datetime.utcnow().isoformat())
    results: list[dict[str, Any]] = []
    for index, url in enumerate(urls, start=1):
        _update(run_id, current_index=index, current_url=url)
        try:
            started = start_production_ingestion(
                url=url,
                candidate_limit=candidate_limit,
                parallel_workers=parallel_workers,
            )
            task_id = str(started["task_id"])
            final = _wait_task(task_id, per_product_timeout_seconds)
            results.append({
                "index": index,
                "url": url,
                "task_id": task_id,
                "status": final.get("status"),
                "global_product_id": final.get("global_product_id"),
                "duration_seconds": final.get("duration_seconds"),
                "newly_saved_offer_count": final.get("newly_saved_offer_count"),
                "quarantined_offer_count": final.get("quarantined_offer_count"),
                "duplicate_detected": final.get("duplicate_detected"),
                "error": final.get("error"),
            })
        except Exception as exc:
            results.append({
                "index": index,
                "url": url,
                "status": "FAILED_TO_START",
                "error": f"{type(exc).__name__}: {exc}",
            })
        _update(run_id, results=list(results), completed_product_count=len(results))

    success_count = sum(1 for r in results if r.get("status") == "COMPLETED")
    failed_count = len(results) - success_count
    _update(
        run_id,
        status="COMPLETED",
        finished_at=datetime.utcnow().isoformat(),
        results=results,
        success_count=success_count,
        failed_count=failed_count,
        success_rate_percent=round(success_count / len(results) * 100, 2) if results else 0.0,
        current_url=None,
    )


def start_stress_run(*, urls: list[str], candidate_limit: int = 50, parallel_workers: int = 3, per_product_timeout_seconds: int = 300) -> dict[str, Any]:
    cleaned = [str(url or "").strip() for url in urls if str(url or "").strip()]
    if not cleaned:
        raise ValueError("En az bir ürün URL'si gerekli.")
    if len(cleaned) > 10:
        raise ValueError("Kontrollü stress testi tek batch'te en fazla 10 ürün kabul eder.")

    run_id = uuid4().hex
    row = {
        "engine": ENGINE,
        "engine_version": VERSION,
        "run_id": run_id,
        "status": "QUEUED",
        "product_count": len(cleaned),
        "completed_product_count": 0,
        "candidate_limit": int(candidate_limit),
        "parallel_workers": int(parallel_workers),
        "per_product_timeout_seconds": int(per_product_timeout_seconds),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "results": [],
    }
    with _lock:
        _runs[run_id] = row
    _executor.submit(_run, run_id, cleaned, int(candidate_limit), int(parallel_workers), int(per_product_timeout_seconds))
    return dict(row)
