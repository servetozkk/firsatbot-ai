from __future__ import annotations

import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from app.services.bulk_ingestion_v232_service import (
    get_bulk_run,
    start_bulk_ingestion,
)

ENGINE = "FIRSATAI_PRODUCTION_STRESS_V238"
VERSION = "23.8.0"
BASE_DIR = Path(__file__).resolve().parents[2]
STATE_PATH = BASE_DIR / "data" / "production_stress_v238.json"

_lock = RLock()
_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="v238-production-stress",
)
_runs: dict[str, dict[str, Any]] = {}


def _empty_state() -> dict[str, Any]:
    return {"version": VERSION, "updated_at": None, "runs": []}


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
        merged = {
            str(row.get("stress_run_id") or ""): dict(row)
            for row in data.get("runs", [])
            if isinstance(row, dict)
        }
        for run_id, row in _runs.items():
            merged[run_id] = dict(row)
        rows = sorted(
            merged.values(),
            key=lambda row: str(row.get("created_at") or ""),
        )[-100:]
        data["version"] = VERSION
        data["updated_at"] = datetime.utcnow().isoformat()
        data["runs"] = rows
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


def _clean_urls(urls: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    seen: set[str] = set()
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
        out.append(url)
    return out, duplicate_count


def _normalized_category(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "UNKNOWN"
    # Full breadcrumb yerine raporda son kategori daha anlamlı.
    for sep in (">", "›", "»", "|"):
        if sep in text:
            parts = [part.strip() for part in text.split(sep) if part.strip()]
            if parts:
                return parts[-1]
    return text


def _error_type(value: Any) -> str:
    text = str(value or "").upper()
    if not text:
        return "NONE"
    if "SECURITY_CHALLENGE" in text:
        return "SECURITY_CHALLENGE"
    if "NO_BUYABLE_OFFER" in text:
        return "NO_BUYABLE_OFFER"
    if "TIMEOUT" in text:
        return "TIMEOUT"
    if "PRODUCT_NOT_FOUND" in text or "ADAY" in text:
        return "PRODUCT_NOT_FOUND"
    return "ERROR"


def build_stress_report(bulk: dict[str, Any]) -> dict[str, Any]:
    results = list(bulk.get("results") or [])
    total = len(results)
    completed = sum(
        1 for item in results
        if str(item.get("status") or "").upper() == "COMPLETED"
    )
    failed = total - completed

    served_product_count = sum(
        1 for item in results
        if int(item.get("served_offer_count") or 0) > 0
    )
    zero_serving_items = [
        {
            "index": item.get("index"),
            "url": item.get("url"),
            "global_product_id": item.get("global_product_id"),
            "status": item.get("status"),
            "error": item.get("error"),
        }
        for item in results
        if str(item.get("status") or "").upper() == "COMPLETED"
        and int(item.get("served_offer_count") or 0) <= 0
    ]

    category_counts: Counter = Counter(
        _normalized_category(item.get("category"))
        for item in results
    )
    product_kind_counts: Counter = Counter(
        str(item.get("price_integrity_product_kind") or "unknown")
        for item in results
    )
    product_subkind_counts: Counter = Counter(
        str(item.get("price_integrity_product_subkind") or "unknown")
        for item in results
    )
    error_counts: Counter = Counter(
        _error_type(item.get("error"))
        for item in results
        if item.get("error")
    )

    total_saved = sum(int(item.get("newly_saved_offer_count") or 0) for item in results)
    total_served = sum(int(item.get("served_offer_count") or 0) for item in results)
    total_quarantine = sum(int(item.get("quarantined_offer_count") or 0) for item in results)
    served_store_sum = sum(int(item.get("served_store_count") or 0) for item in results)

    canonical = dict(bulk.get("canonical_lifecycle") or {})
    single_source = canonical.get("single_source_of_truth") is True
    duplicate_group_count = int(
        canonical.get("duplicate_product_group_identity_count") or 0
    )
    duplicate_global_count = int(
        canonical.get("duplicate_global_product_identity_count") or 0
    )
    identity_violation_count = int(
        canonical.get("identity_contract_violation_count") or 0
    )
    duplicate_ingestion_count = int(bulk.get("duplicate_ingestion_count") or 0)

    price_audit = dict(bulk.get("batch_price_integrity") or {})
    audit_error_count = sum(
        1 for row in price_audit.values()
        if isinstance(row, dict) and row.get("error")
    )

    # Şeffaf operasyonel skor; ticari kalite puanı değildir.
    ingestion_ratio = (completed / total) if total else 0.0
    serving_ratio = (served_product_count / completed) if completed else 0.0
    unique_expected = completed if completed else 1
    unique_ratio = min(
        1.0,
        int(bulk.get("unique_global_product_count") or 0) / unique_expected,
    )
    canonical_ratio = 1.0 if (
        single_source
        and duplicate_group_count == 0
        and duplicate_global_count == 0
        and identity_violation_count == 0
    ) else 0.0
    audit_ratio = 1.0 if audit_error_count == 0 else max(
        0.0, 1.0 - audit_error_count / max(1, len(price_audit))
    )

    score = round(
        ingestion_ratio * 35
        + canonical_ratio * 25
        + serving_ratio * 20
        + unique_ratio * 10
        + audit_ratio * 10,
        2,
    )

    if score >= 90 and failed == 0 and single_source and audit_error_count == 0:
        readiness = "READY"
    elif score >= 75:
        readiness = "WATCH"
    else:
        readiness = "NOT_READY"

    warnings: list[str] = []
    if failed:
        warnings.append(f"{failed} ürün ingestion başarısız.")
    if zero_serving_items:
        warnings.append(
            f"{len(zero_serving_items)} tamamlanan üründe kullanıcıya servis edilen teklif yok."
        )
    if not single_source:
        warnings.append("Canonical lifecycle single_source_of_truth=false.")
    if duplicate_group_count or duplicate_global_count:
        warnings.append(
            "Canonical duplicate tespit edildi: "
            f"group={duplicate_group_count}, global={duplicate_global_count}."
        )
    if identity_violation_count:
        warnings.append(
            f"Identity contract violation={identity_violation_count}."
        )
    if duplicate_ingestion_count:
        warnings.append(
            f"Duplicate ingestion={duplicate_ingestion_count}."
        )
    if audit_error_count:
        warnings.append(
            f"Final price-integrity audit error={audit_error_count}."
        )

    return {
        "engine": ENGINE,
        "engine_version": VERSION,
        "readiness": readiness,
        "stress_score": score,
        "score_note": (
            "Operational stress score: ingestion 35, canonical 25, "
            "serving 20, unique identity 10, final price audit 10."
        ),
        "product_count": total,
        "completed_count": completed,
        "failed_count": failed,
        "success_rate_percent": round(ingestion_ratio * 100, 2) if total else None,
        "unique_global_product_count": int(
            bulk.get("unique_global_product_count") or 0
        ),
        "duplicate_input_url_count": int(
            bulk.get("duplicate_input_url_count") or 0
        ),
        "duplicate_ingestion_count": duplicate_ingestion_count,
        "newly_saved_offer_count": total_saved,
        "served_offer_count": total_served,
        "quarantined_offer_count": total_quarantine,
        "served_product_count": served_product_count,
        "zero_serving_product_count": len(zero_serving_items),
        "average_served_store_count": (
            round(served_store_sum / completed, 2)
            if completed else None
        ),
        "category_counts": dict(category_counts),
        "product_kind_counts": dict(product_kind_counts),
        "product_subkind_counts": dict(product_subkind_counts),
        "error_types": dict(error_counts),
        "price_audit_error_count": audit_error_count,
        "canonical": {
            "single_source_of_truth": single_source,
            "duplicate_product_group_identity_count": duplicate_group_count,
            "duplicate_global_product_identity_count": duplicate_global_count,
            "identity_contract_violation_count": identity_violation_count,
        },
        "warnings": warnings,
        "zero_serving_products": zero_serving_items,
        "products": [
            {
                "index": item.get("index"),
                "status": item.get("status"),
                "global_product_id": item.get("global_product_id"),
                "identity_source": item.get("identity_source"),
                "category": item.get("category"),
                "product_kind": item.get("price_integrity_product_kind"),
                "product_subkind": item.get("price_integrity_product_subkind"),
                "newly_saved_offer_count": int(
                    item.get("newly_saved_offer_count") or 0
                ),
                "served_offer_count": int(
                    item.get("served_offer_count") or 0
                ),
                "served_store_count": int(
                    item.get("served_store_count") or 0
                ),
                "served_store_codes": list(
                    item.get("served_store_codes") or []
                ),
                "served_best_price": item.get("served_best_price"),
                "quarantined_offer_count": int(
                    item.get("quarantined_offer_count") or 0
                ),
                "duplicate_detected": bool(item.get("duplicate_detected")),
                "duration_seconds": item.get("duration_seconds"),
                "error": item.get("error"),
                "url": item.get("url"),
            }
            for item in results
        ],
    }


def _execute_stress(
    stress_run_id: str,
    *,
    urls: list[str],
    candidate_limit: int,
    parallel_workers: int,
    per_product_timeout_seconds: int,
) -> None:
    _update(
        stress_run_id,
        status="RUNNING",
        stage="STARTING_BULK",
        started_at=datetime.utcnow().isoformat(),
    )
    try:
        bulk = start_bulk_ingestion(
            urls=urls,
            candidate_limit=candidate_limit,
            parallel_workers=parallel_workers,
            per_product_timeout_seconds=per_product_timeout_seconds,
        )
        bulk_run_id = str(bulk.get("run_id") or "")
        if not bulk_run_id:
            raise RuntimeError("Bulk ingestion run_id üretmedi.")
        _update(
            stress_run_id,
            bulk_run_id=bulk_run_id,
            stage="WAITING_BULK",
        )

        while True:
            current = get_bulk_run(bulk_run_id)
            if current is None:
                raise RuntimeError("Bulk run kayboldu.")
            _update(
                stress_run_id,
                bulk_status=current.get("status"),
                processed_count=int(current.get("processed_count") or 0),
                completed_count=int(current.get("completed_count") or 0),
                failed_count=int(current.get("failed_count") or 0),
                current_index=int(current.get("current_index") or 0),
                current_url=current.get("current_url"),
            )
            status = str(current.get("status") or "").upper()
            if status in {"COMPLETED", "FAILED"}:
                break
            time.sleep(2.0)

        report = build_stress_report(current)
        _update(
            stress_run_id,
            status="COMPLETED",
            stage="READY",
            finished_at=datetime.utcnow().isoformat(),
            report=report,
            readiness=report.get("readiness"),
            stress_score=report.get("stress_score"),
            processed_count=report.get("product_count"),
            completed_count=report.get("completed_count"),
            failed_count=report.get("failed_count"),
        )
    except Exception as exc:
        _update(
            stress_run_id,
            status="FAILED",
            stage="FAILED",
            finished_at=datetime.utcnow().isoformat(),
            error=f"{type(exc).__name__}: {exc}",
        )


def start_production_stress(
    *,
    urls: list[str],
    candidate_limit: int = 50,
    parallel_workers: int = 3,
    per_product_timeout_seconds: int = 300,
) -> dict[str, Any]:
    cleaned, duplicate_input = _clean_urls(urls)
    if len(cleaned) != 10:
        raise ValueError(
            "V23.8 production stress testi tam olarak 10 benzersiz ürün URL'si gerektirir."
        )

    run_id = uuid4().hex
    now = datetime.utcnow().isoformat()
    row = {
        "engine": ENGINE,
        "engine_version": VERSION,
        "stress_run_id": run_id,
        "bulk_run_id": None,
        "status": "QUEUED",
        "stage": "QUEUED",
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "input_url_count": len(urls),
        "unique_url_count": len(cleaned),
        "duplicate_input_url_count": duplicate_input,
        "processed_count": 0,
        "completed_count": 0,
        "failed_count": 0,
        "current_index": 0,
        "current_url": None,
        "readiness": None,
        "stress_score": None,
        "report": None,
        "error": None,
        "candidate_limit": int(candidate_limit),
        "parallel_workers": int(parallel_workers),
        "per_product_timeout_seconds": int(per_product_timeout_seconds),
    }
    with _lock:
        _runs[run_id] = row
    _save_state()
    _executor.submit(
        _execute_stress,
        run_id,
        urls=cleaned,
        candidate_limit=int(candidate_limit),
        parallel_workers=int(parallel_workers),
        per_product_timeout_seconds=int(per_product_timeout_seconds),
    )
    return dict(row)


def get_stress_run(stress_run_id: str) -> dict[str, Any] | None:
    key = str(stress_run_id or "").strip()
    with _lock:
        row = _runs.get(key)
        if row is not None:
            return dict(row)
    state = _load_state()
    for row in state.get("runs", []):
        if str(row.get("stress_run_id") or "") == key:
            return dict(row)
    return None


def list_stress_runs(limit: int = 20) -> list[dict[str, Any]]:
    state = _load_state()
    merged = {
        str(row.get("stress_run_id") or ""): dict(row)
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
    return rows[:max(1, min(int(limit), 100))]


def stress_runtime_info() -> dict[str, Any]:
    return {
        "engine": ENGINE,
        "engine_version": VERSION,
        "required_unique_product_count": 10,
        "execution": "v23.7-bulk-sequential-products-plus-per-store-parallelism",
        "final_gates": (
            "ingestion,canonical-single-source,duplicate,serving,"
            "price-integrity"
        ),
        "readiness_thresholds": "READY>=90,WATCH>=75,NOT_READY<75",
        "persistent_state": str(STATE_PATH),
    }
