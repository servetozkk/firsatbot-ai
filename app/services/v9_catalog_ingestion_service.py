from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct
from app.services.catalog_reconciliation_service import (
    process_reconciliation_queue,
)
from app.services.catalog_scan_plan_service import (
    get_active_catalog_plans,
    get_catalog_plan,
)
from app.services.category_discovery_service import (
    CategoryDiscoveryService,
)
from app.services.operational_log_service import record_operation_event
from app.services.scraper_resilience_service import assert_circuit_closed, get_store_health
from app.services.workload_priority_v23612 import user_deep_priority_active_v23612


STATE_PATH = Path("data/v9_catalog_schedule_state.json")
HISTORY_PATH = Path("data/v9_catalog_ingestion_history.json")
_LOCK = threading.RLock()
_RUNNING_PLAN_IDS: set[str] = set()


def _now() -> datetime:
    return datetime.now().astimezone()


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat(timespec="seconds")


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def get_schedule_state() -> dict[str, Any]:
    with _LOCK:
        value = _read_json(STATE_PATH, {})
    return value if isinstance(value, dict) else {}


def _set_plan_state(plan_id: str, **changes: Any) -> None:
    with _LOCK:
        state = _read_json(STATE_PATH, {})
        if not isinstance(state, dict):
            state = {}
        row = state.setdefault(plan_id, {})
        row.update(changes)
        _write_json(STATE_PATH, state)


def ingestion_history(limit: int = 30) -> list[dict[str, Any]]:
    with _LOCK:
        rows = _read_json(HISTORY_PATH, [])
    if not isinstance(rows, list):
        return []
    return list(reversed(rows[-max(1, limit):]))


def _append_history(row: dict[str, Any]) -> None:
    with _LOCK:
        rows = _read_json(HISTORY_PATH, [])
        if not isinstance(rows, list):
            rows = []
        rows.append(row)
        _write_json(HISTORY_PATH, rows[-300:])


def _global_coverage_snapshot(db) -> dict[str, int]:
    global_products = db.query(GlobalProduct).count()
    active_offers = (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == "ACTIVE",
        )
        .count()
    )
    multi_store_products = (
        db.query(GlobalOffer.global_product_id)
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == "ACTIVE",
        )
        .group_by(GlobalOffer.global_product_id)
        .having(
            __import__("sqlalchemy").func.count(
                __import__("sqlalchemy").distinct(
                    GlobalOffer.store_code
                )
            ) >= 2
        )
        .count()
    )
    return {
        "global_products": global_products,
        "active_global_offers": active_offers,
        "multi_store_products": multi_store_products,
    }


def _scan_source(
    service: CategoryDiscoveryService,
    *,
    source: dict[str, Any],
    limit: int,
) -> dict[str, Any]:
    try:
        assert_circuit_closed(source["store_code"])
        try:
            result = service.scan_and_save(
                category_url=source["url"],
                limit=limit,
                reconcile_across_stores=False,
            )
        except TypeError:
            result = service.scan_and_save(
                category_url=source["url"],
                limit=limit,
            )

        data = result.to_dict()
        return {
            "store_code": source["store_code"],
            "store_name": source["store_name"],
            "success": bool(data.get("success")),
            "found_count": int(data.get("found_count", 0)),
            "saved_count": int(data.get("saved_count", 0)),
            "updated_count": int(data.get("updated_count", 0)),
            "error_count": int(data.get("error_count", 0)),
            "warnings": list(data.get("warnings", []))[-20:],
        }
    except Exception as error:
        return {
            "store_code": source["store_code"],
            "store_name": source["store_name"],
            "success": False,
            "found_count": 0,
            "saved_count": 0,
            "updated_count": 0,
            "error_count": 1,
            "error": f"{type(error).__name__}: {error}",
        }


def run_catalog_plan(plan: dict[str, Any]) -> dict[str, Any]:
    run_id = str(uuid4())
    if user_deep_priority_active_v23612():
        now_v23614 = _now()
        print(
            "V23.61.4 V9 PLAN YIELD:",
            f"plan={plan.get('name', plan.get('id'))}",
            "reason=USER_INGESTION_PRIORITY_ACTIVE",
        )
        return {
            "run_id": run_id,
            "plan_id": str(plan.get("id") or ""),
            "plan_name": plan.get("name", str(plan.get("id") or "")),
            "status": "yielded_user_ingestion_priority",
            "started_at": _iso(now_v23614),
            "finished_at": _iso(now_v23614),
            "duration_seconds": 0,
            "store_count": 0,
            "successful_store_count": 0,
            "failed_store_count": 0,
            "found_count": 0,
            "saved_count": 0,
            "updated_count": 0,
            "new_global_products": 0,
            "new_active_offers": 0,
            "new_multi_store_products": 0,
            "results": [],
        }
    started = _now()
    plan_id = str(plan["id"])
    with _LOCK:
        if plan_id in _RUNNING_PLAN_IDS:
            return {"run_id":run_id,"plan_id":plan_id,"plan_name":plan.get("name",plan_id),"status":"skipped_already_running","started_at":_iso(started),"finished_at":_iso(started),"duration_seconds":0,"store_count":0,"successful_store_count":0,"failed_store_count":0,"found_count":0,"saved_count":0,"updated_count":0,"new_global_products":0,"new_active_offers":0,"new_multi_store_products":0,"results":[]}
        _RUNNING_PLAN_IDS.add(plan_id)
    sources = [
        item
        for item in plan.get("sources", [])
        if item.get("active", True)
    ]
    limit = int(plan.get("limit", 100) or 100)

    _set_plan_state(
        plan_id,
        status="running",
        run_id=run_id,
        started_at=_iso(started),
        last_error=None,
    )

    before = {}
    with SessionLocal() as db:
        before = _global_coverage_snapshot(db)

    results: list[dict[str, Any]] = []
    # Browser profili kullanan mağazalar sıralı çalışır.
    sequential_codes = {"n11"}
    parallel_sources = [
        item for item in sources
        if item["store_code"] not in sequential_codes
    ]
    sequential_sources = [
        item for item in sources
        if item["store_code"] in sequential_codes
    ]

    if parallel_sources:
        with ThreadPoolExecutor(
            max_workers=min(3, len(parallel_sources)),
            thread_name_prefix="v9-catalog-ingestion",
        ) as executor:
            futures = [
                executor.submit(
                    _scan_source,
                    CategoryDiscoveryService(),
                    source=source,
                    limit=limit,
                )
                for source in parallel_sources
            ]
            for future in futures:
                results.append(future.result())

    for source in sequential_sources:
        results.append(
            _scan_source(
                CategoryDiscoveryService(),
                source=source,
                limit=limit,
            )
        )

    with SessionLocal() as db:
        reconciliation = process_reconciliation_queue(
            db=db,
            limit=5000,
            retry_failed=True,
        )
        after = _global_coverage_snapshot(db)

    finished = _now()
    interval = max(
        15,
        int(plan.get("interval_minutes", 60) or 60),
    )
    next_run = finished + timedelta(minutes=interval)
    failed_stores = [
        item for item in results if not item.get("success")
    ]

    row = {
        "run_id": run_id,
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "status": (
            "completed"
            if not failed_stores
            else "completed_with_errors"
        ),
        "started_at": _iso(started),
        "finished_at": _iso(finished),
        "next_run_at": _iso(next_run),
        "duration_seconds": round(
            (finished - started).total_seconds(),
            2,
        ),
        "store_count": len(sources),
        "successful_store_count": (
            len(sources) - len(failed_stores)
        ),
        "failed_store_count": len(failed_stores),
        "found_count": sum(
            int(item.get("found_count", 0))
            for item in results
        ),
        "saved_count": sum(
            int(item.get("saved_count", 0))
            for item in results
        ),
        "updated_count": sum(
            int(item.get("updated_count", 0))
            for item in results
        ),
        "reconciliation": reconciliation,
        "coverage_before": before,
        "coverage_after": after,
        "new_global_products": (
            after["global_products"] - before["global_products"]
        ),
        "new_active_offers": (
            after["active_global_offers"]
            - before["active_global_offers"]
        ),
        "new_multi_store_products": (
            after["multi_store_products"]
            - before["multi_store_products"]
        ),
        "results": results,
    }

    record_operation_event(level=("WARNING" if row["failed_store_count"] > 0 else "INFO"), source="catalog_ingestion", event_type="plan_completed", message=f"{row['plan_name']} tamamlandı: {row['successful_store_count']}/{row['store_count']} mağaza başarılı", details={"plan_id": row["plan_id"], "status": row["status"], "found_count": row["found_count"], "saved_count": row["saved_count"], "failed_store_count": row["failed_store_count"]})
    _append_history(row)
    _set_plan_state(
        plan_id,
        status=row["status"],
        last_run_at=row["finished_at"],
        next_run_at=row["next_run_at"],
        last_run_id=run_id,
        last_error=(
            f"{len(failed_stores)} mağazada hata"
            if failed_stores
            else None
        ),
        last_result={
            "found_count": row["found_count"],
            "saved_count": row["saved_count"],
            "new_global_products": row["new_global_products"],
            "new_active_offers": row["new_active_offers"],
            "new_multi_store_products": row["new_multi_store_products"],
        },
    )
    with _LOCK:
        _RUNNING_PLAN_IDS.discard(plan_id)
    return row


def run_plan_by_id(plan_id: str) -> dict[str, Any]:
    plan = get_catalog_plan(plan_id)
    if plan is None:
        raise ValueError("Katalog planı bulunamadı.")
    return run_catalog_plan(plan)


def run_all_active_plans() -> dict[str, Any]:
    plans = get_active_catalog_plans()
    results = [run_catalog_plan(plan) for plan in plans]
    return {
        "catalog_count": len(results),
        "found_count": sum(
            item["found_count"] for item in results
        ),
        "saved_count": sum(
            item["saved_count"] for item in results
        ),
        "new_global_products": sum(
            item["new_global_products"] for item in results
        ),
        "new_active_offers": sum(
            item["new_active_offers"] for item in results
        ),
        "new_multi_store_products": sum(
            item["new_multi_store_products"]
            for item in results
        ),
        "results": results,
    }


def run_due_catalog_plans() -> dict[str, Any]:
    now = _now()
    if user_deep_priority_active_v23612():
        print("V23.61.4 V9 SCHEDULER YIELD: user-ingestion-priority-active.")
        return {
            "checked_at": _iso(now),
            "due_catalog_count": 0,
            "yielded": True,
            "yield_reason": "USER_INGESTION_PRIORITY_ACTIVE",
            "results": [],
        }
    state = get_schedule_state()
    due: list[dict[str, Any]] = []

    for plan in get_active_catalog_plans():
        row = state.get(str(plan["id"]), {})
        next_text = row.get("next_run_at")
        if not next_text:
            due.append(plan)
            continue
        try:
            next_run = datetime.fromisoformat(next_text)
        except ValueError:
            due.append(plan)
            continue
        if next_run <= now:
            due.append(plan)

    results = [run_catalog_plan(plan) for plan in due]
    return {
        "checked_at": _iso(now),
        "due_catalog_count": len(due),
        "results": results,
    }
