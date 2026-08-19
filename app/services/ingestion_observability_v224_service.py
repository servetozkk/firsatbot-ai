from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any

from app.database.database import SessionLocal
from app.database.models import GlobalProduct, ProductGroup

ENGINE = "FIRSATAI_PRODUCTION_INGESTION_OBSERVABILITY"
VERSION = "22.4.0"
BASE_DIR = Path(__file__).resolve().parents[2]
STATE_PATH = BASE_DIR / "data" / "ingestion_observability_v224.json"
_lock = RLock()


def _empty() -> dict[str, Any]:
    return {"version": VERSION, "updated_at": None, "tasks": []}


def _load() -> dict[str, Any]:
    with _lock:
        if not STATE_PATH.exists():
            return _empty()
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return _empty()
            data.setdefault("tasks", [])
            return data
        except Exception:
            return _empty()


def _save(data: dict[str, Any]) -> None:
    with _lock:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data["version"] = VERSION
        data["updated_at"] = datetime.utcnow().isoformat()
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        tmp.replace(STATE_PATH)


def record_ingestion_result(row: dict[str, Any]) -> None:
    data = _load()
    tasks = [item for item in data.get("tasks", []) if item.get("task_id") != row.get("task_id")]
    tasks.append(dict(row))
    # Son 500 ingestion yeterli; kalıcı dosyanın sınırsız büyümesini engeller.
    data["tasks"] = tasks[-500:]
    _save(data)


def get_recent_tasks(limit: int = 50) -> list[dict[str, Any]]:
    data = _load()
    tasks = list(data.get("tasks", []))
    tasks.reverse()
    return tasks[: max(1, min(int(limit), 500))]


def get_product_history(global_product_id: int, limit: int = 50) -> list[dict[str, Any]]:
    product_id = int(global_product_id)
    rows = [
        row for row in get_recent_tasks(500)
        if int(row.get("global_product_id") or 0) == product_id
    ]
    return rows[: max(1, min(int(limit), 500))]


def duplicate_snapshot(identity_key: str | None, global_product_id: int | None) -> dict[str, Any]:
    key = str(identity_key or "").strip()
    db = SessionLocal()
    try:
        group_count = (
            db.query(ProductGroup).filter(ProductGroup.group_key == key).count()
            if key else 0
        )
        global_count = (
            db.query(GlobalProduct).filter(GlobalProduct.identity_key == key).count()
            if key else 0
        )
        active_global_id_count = 0
        if global_product_id:
            active_global_id_count = (
                db.query(GlobalProduct)
                .filter(GlobalProduct.id == int(global_product_id), GlobalProduct.status == "ACTIVE")
                .count()
            )
        return {
            "canonical_product_group_count": int(group_count),
            "canonical_global_product_count": int(global_count),
            "target_global_product_active_count": int(active_global_id_count),
            "duplicate_detected": bool(group_count > 1 or global_count > 1),
        }
    finally:
        db.close()


def _store_counts(task: dict[str, Any]) -> tuple[int, int, Counter]:
    results = task.get("store_results") or []
    successes = 0
    failures = 0
    errors: Counter = Counter()
    for row in results:
        if bool(row.get("success")):
            successes += 1
        else:
            failures += 1
            status = str(row.get("status") or row.get("message") or "ERROR")
            if "SECURITY_CHALLENGE" in status:
                errors["SECURITY_CHALLENGE"] += 1
            elif "Ürün adayı bulunamadı" in status or "Urun adayi bulunamadi" in status:
                errors["PRODUCT_NOT_FOUND"] += 1
            else:
                errors["ERROR"] += 1
    return successes, failures, errors


def get_summary() -> dict[str, Any]:
    tasks = get_recent_tasks(500)
    completed = [t for t in tasks if t.get("status") == "COMPLETED"]
    failed = [t for t in tasks if t.get("status") == "FAILED"]
    durations = [float(t.get("duration_seconds") or 0) for t in completed if float(t.get("duration_seconds") or 0) > 0]
    store_success = 0
    store_failure = 0
    error_types: Counter = Counter()
    saved_offers = 0
    quarantines = 0
    duplicates = 0
    categories: Counter = Counter()

    for task in tasks:
        s, f, e = _store_counts(task)
        store_success += s
        store_failure += f
        error_types.update(e)
        saved_offers += int(task.get("newly_saved_offer_count") or 0)
        quarantines += int(task.get("quarantined_offer_count") or 0)
        duplicates += 1 if task.get("duplicate_detected") else 0
        category = str(task.get("category") or "UNKNOWN")
        categories[category] += 1

    store_total = store_success + store_failure
    return {
        "engine": ENGINE,
        "engine_version": VERSION,
        "recorded_ingestion_count": len(tasks),
        "completed_count": len(completed),
        "failed_count": len(failed),
        "success_rate_percent": round((len(completed) / len(tasks) * 100), 2) if tasks else None,
        "average_duration_seconds": round(sum(durations) / len(durations), 2) if durations else None,
        "max_duration_seconds": round(max(durations), 2) if durations else None,
        "store_attempt_count": store_total,
        "store_success_count": store_success,
        "store_failure_count": store_failure,
        "store_success_rate_percent": round((store_success / store_total * 100), 2) if store_total else None,
        "newly_saved_offer_count": saved_offers,
        "quarantined_offer_count": quarantines,
        "duplicate_ingestion_count": duplicates,
        "error_types": dict(error_types),
        "category_counts": dict(categories),
        "recent_tasks": tasks[:10],
    }
