from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from app.services.production_ingestion_v220_service import (
    get_ingestion_task,
    start_production_ingestion,
)
from app.services.canonical_lifecycle_v230_service import (
    lifecycle_status,
)
from app.database.database import SessionLocal
from app.services.price_integrity_v219_service import (
    audit_product_prices,
    get_price_integrity_status,
)

ENGINE = "FIRSATAI_BULK_CATALOG_INGESTION"
VERSION = "23.8.0"
BASE_DIR = Path(__file__).resolve().parents[2]
STATE_PATH = BASE_DIR / "data" / "bulk_ingestion_v232.json"

_lock = RLock()
_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="v232-bulk-ingestion",
)
_runs: dict[str, dict[str, Any]] = {}


def _empty_state() -> dict[str, Any]:
    return {
        "version": VERSION,
        "updated_at": None,
        "runs": [],
    }


def _load_state() -> dict[str, Any]:
    with _lock:
        if not STATE_PATH.exists():
            return _empty_state()
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return _empty_state()
            data.setdefault("runs", [])
            return data
        except Exception:
            return _empty_state()


def _save_state() -> None:
    with _lock:
        data = _load_state()
        existing = {
            str(row.get("run_id") or ""): row
            for row in data.get("runs", [])
            if isinstance(row, dict)
        }
        for run_id, row in _runs.items():
            existing[run_id] = dict(row)

        ordered = sorted(
            existing.values(),
            key=lambda row: str(row.get("created_at") or ""),
        )
        data["runs"] = ordered[-100:]
        data["version"] = VERSION
        data["updated_at"] = datetime.utcnow().isoformat()
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        tmp.replace(STATE_PATH)


def _update(run_id: str, **changes: Any) -> None:
    with _lock:
        row = _runs.get(run_id)
        if row is None:
            return
        row.update(changes)
        row["updated_at"] = datetime.utcnow().isoformat()
    _save_state()


def _dedupe_urls(urls: list[str]) -> tuple[list[str], int]:
    seen: set[str] = set()
    cleaned: list[str] = []
    duplicate_count = 0
    for raw in urls:
        url = str(raw or "").strip()
        if not url:
            continue
        key = url.casefold()
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        cleaned.append(url)
    return cleaned, duplicate_count


def _wait_for_task(
    task_id: str,
    *,
    timeout_seconds: int,
    poll_seconds: float = 1.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(30, int(timeout_seconds))
    last: dict[str, Any] | None = None

    while time.monotonic() < deadline:
        row = get_ingestion_task(task_id)
        if row is not None:
            last = row
            status = str(row.get("status") or "").upper()
            if status in {"COMPLETED", "FAILED"}:
                return row
        time.sleep(max(0.5, float(poll_seconds)))

    return {
        **(last or {}),
        "task_id": task_id,
        "status": "FAILED",
        "stage": "BULK_TIMEOUT",
        "error": f"BULK_TIMEOUT after {int(timeout_seconds)} seconds",
    }


def _item_summary(
    *,
    index: int,
    url: str,
    task: dict[str, Any],
) -> dict[str, Any]:
    return {
        "index": int(index),
        "url": url,
        "task_id": task.get("task_id"),
        "status": task.get("status"),
        "stage": task.get("stage"),
        "global_product_id": task.get("global_product_id"),
        "identity_key": task.get("identity_key"),
        "identity_source": task.get("identity_source"),
        "category": task.get("category"),
        "duration_seconds": task.get("duration_seconds"),
        "newly_saved_offer_count": int(
            task.get("newly_saved_offer_count") or 0
        ),
        "active_offer_count": int(
            task.get("active_offer_count") or 0
        ),
        "active_store_count": int(
            task.get("active_store_count") or 0
        ),
        "active_store_codes": list(
            task.get("active_store_codes") or []
        ),
        "quarantined_offer_count": int(
            task.get("quarantined_offer_count") or 0
        ),
        "served_best_price": task.get("served_best_price"),
        "served_offer_count": int(task.get("served_offer_count") or 0),
        "served_store_count": int(task.get("served_store_count") or 0),
        "served_store_codes": list(task.get("served_store_codes") or []),
        "duplicate_detected": bool(
            task.get("duplicate_detected")
        ),
        "error": task.get("error"),
    }


def _execute_run(
    run_id: str,
    *,
    urls: list[str],
    candidate_limit: int,
    parallel_workers: int,
    per_product_timeout_seconds: int,
) -> None:
    started = time.perf_counter()
    _update(
        run_id,
        status="RUNNING",
        stage="INGESTING",
        started_at=datetime.utcnow().isoformat(),
    )

    results: list[dict[str, Any]] = []
    completed_count = 0
    failed_count = 0
    total_saved_offers = 0
    duplicate_count = 0
    global_ids: list[int] = []

    for index, url in enumerate(urls, start=1):
        _update(
            run_id,
            current_index=index,
            current_url=url,
            processed_count=index - 1,
            completed_count=completed_count,
            failed_count=failed_count,
            newly_saved_offer_count=total_saved_offers,
        )
        try:
            queued = start_production_ingestion(
                url=url,
                candidate_limit=candidate_limit,
                parallel_workers=parallel_workers,
                fast_ingest=False,
            )
            task_id = str(queued.get("task_id") or "")
            if not task_id:
                raise RuntimeError(
                    "Production ingestion task_id üretmedi."
                )
            final = _wait_for_task(
                task_id,
                timeout_seconds=per_product_timeout_seconds,
            )
        except Exception as exc:
            final = {
                "task_id": None,
                "status": "FAILED",
                "stage": "BULK_SOURCE_FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            }

        summary = _item_summary(
            index=index,
            url=url,
            task=final,
        )
        results.append(summary)

        if str(summary.get("status") or "").upper() == "COMPLETED":
            completed_count += 1
        else:
            failed_count += 1

        total_saved_offers += int(
            summary.get("newly_saved_offer_count") or 0
        )
        if summary.get("duplicate_detected"):
            duplicate_count += 1

        gp_id = summary.get("global_product_id")
        if gp_id is not None:
            try:
                global_ids.append(int(gp_id))
            except (TypeError, ValueError):
                pass

        _update(
            run_id,
            results=list(results),
            processed_count=index,
            completed_count=completed_count,
            failed_count=failed_count,
            newly_saved_offer_count=total_saved_offers,
            duplicate_ingestion_count=duplicate_count,
            global_product_ids=sorted(set(global_ids)),
        )

    # V23.7: Batch kapanmadan persisted DB üzerinde son bir fiyat-integrity
    # audit'i çalıştır. Production task zaten audit yapar; bu katman restart/
    # orchestration sınırında son güvenlik kapısı ve raporlama görevidir.
    batch_price_integrity: dict[str, Any] = {}
    for gp_id in sorted(set(global_ids)):
        db = SessionLocal()
        try:
            audit = audit_product_prices(db=db, global_product_id=int(gp_id))
            db.commit()
            serving = get_price_integrity_status(db=db, global_product_id=int(gp_id))
            batch_price_integrity[str(gp_id)] = {
                "audit": audit,
                "serving": serving,
            }
            print(
                "V23.7 bulk final fiyat audit:",
                f"global={gp_id}",
                f"kind={serving.get('product_kind')}/{serving.get('product_subkind')}",
                f"served_best={serving.get('served_best_price')}",
                f"quarantine={serving.get('quarantined_offer_count')}",
            )
        except Exception as exc:
            db.rollback()
            batch_price_integrity[str(gp_id)] = {
                "error": f"{type(exc).__name__}: {exc}",
            }
        finally:
            db.close()

    # Refresh item summaries from the final serving state.
    for item in results:
        gp_id = item.get("global_product_id")
        final_pi = batch_price_integrity.get(str(gp_id), {}) if gp_id is not None else {}
        serving = final_pi.get("serving") or {}
        if serving:
            item["served_best_price"] = serving.get("served_best_price")
            item["served_offer_count"] = int(serving.get("served_offer_count", 0) or 0)
            item["served_store_count"] = int(serving.get("served_store_count", 0) or 0)
            item["served_store_codes"] = list(serving.get("served_store_codes", []) or [])
            item["quarantined_offer_count"] = int(serving.get("quarantined_offer_count", 0) or 0)
            item["price_integrity_product_kind"] = serving.get("product_kind")
            item["price_integrity_product_subkind"] = serving.get("product_subkind")

    lifecycle = lifecycle_status()
    duration = round(time.perf_counter() - started, 3)
    _update(
        run_id,
        status="COMPLETED",
        stage="READY",
        finished_at=datetime.utcnow().isoformat(),
        duration_seconds=duration,
        processed_count=len(urls),
        completed_count=completed_count,
        failed_count=failed_count,
        success_rate_percent=(
            round(completed_count / len(urls) * 100, 2)
            if urls else None
        ),
        newly_saved_offer_count=total_saved_offers,
        duplicate_ingestion_count=duplicate_count,
        unique_global_product_count=len(set(global_ids)),
        global_product_ids=sorted(set(global_ids)),
        batch_price_integrity=batch_price_integrity,
        canonical_lifecycle={
            "duplicate_product_group_identity_count": lifecycle.get(
                "duplicate_product_group_identity_count"
            ),
            "duplicate_global_product_identity_count": lifecycle.get(
                "duplicate_global_product_identity_count"
            ),
            "identity_contract_violation_count": lifecycle.get(
                "identity_contract_violation_count"
            ),
            "single_source_of_truth": lifecycle.get(
                "single_source_of_truth"
            ),
        },
        results=results,
    )


def start_bulk_ingestion(
    *,
    urls: list[str],
    candidate_limit: int = 50,
    parallel_workers: int = 3,
    per_product_timeout_seconds: int = 300,
) -> dict[str, Any]:
    cleaned, duplicate_input_count = _dedupe_urls(urls)
    if not cleaned:
        raise ValueError("En az bir geçerli ürün URL'si gerekli.")
    if len(cleaned) > 100:
        raise ValueError(
            "Tek batch'te en fazla 100 benzersiz ürün URL'si kabul edilir."
        )

    run_id = uuid4().hex
    now = datetime.utcnow().isoformat()
    row = {
        "engine": ENGINE,
        "engine_version": VERSION,
        "run_id": run_id,
        "status": "QUEUED",
        "stage": "QUEUED",
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "duration_seconds": None,
        "input_url_count": len(urls),
        "unique_url_count": len(cleaned),
        "duplicate_input_url_count": duplicate_input_count,
        "processed_count": 0,
        "completed_count": 0,
        "failed_count": 0,
        "success_rate_percent": None,
        "newly_saved_offer_count": 0,
        "duplicate_ingestion_count": 0,
        "unique_global_product_count": 0,
        "global_product_ids": [],
        "candidate_limit": int(candidate_limit),
        "parallel_workers": int(parallel_workers),
        "per_product_timeout_seconds": int(
            per_product_timeout_seconds
        ),
        "current_index": 0,
        "current_url": None,
        "results": [],
        "canonical_lifecycle": None,
    }

    with _lock:
        _runs[run_id] = row
    _save_state()

    _executor.submit(
        _execute_run,
        run_id,
        urls=cleaned,
        candidate_limit=int(candidate_limit),
        parallel_workers=int(parallel_workers),
        per_product_timeout_seconds=int(
            per_product_timeout_seconds
        ),
    )
    return dict(row)


def get_bulk_run(run_id: str) -> dict[str, Any] | None:
    key = str(run_id or "").strip()
    with _lock:
        live = _runs.get(key)
        if live is not None:
            return dict(live)

    state = _load_state()
    for row in state.get("runs", []):
        if str(row.get("run_id") or "") == key:
            return dict(row)
    return None


def list_bulk_runs(limit: int = 20) -> list[dict[str, Any]]:
    state = _load_state()
    merged = {
        str(row.get("run_id") or ""): dict(row)
        for row in state.get("runs", [])
        if isinstance(row, dict)
    }
    with _lock:
        for run_id, row in _runs.items():
            merged[run_id] = dict(row)

    rows = sorted(
        merged.values(),
        key=lambda row: str(row.get("created_at") or ""),
        reverse=True,
    )
    return rows[: max(1, min(int(limit), 100))]


def bulk_runtime_info() -> dict[str, Any]:
    return {
        "engine": ENGINE,
        "engine_version": VERSION,
        "execution_policy": "sequential-products-one-batch-worker",
        "max_unique_urls_per_batch": 100,
        "per_product_pipeline": "production_ingestion_v220",
        "failure_isolation": "per-product",
        "persistent_state": str(STATE_PATH),
    }
