from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime
from threading import RLock, Timer
from typing import Any
from time import perf_counter
from uuid import uuid4

from app.database.database import SessionLocal
from app.database.models import GlobalProduct
from app.services.product_identity_service import ProductIdentityService
from app.services.product_service import save_product
from app.services.scan_service import (
    get_scraper_registry,
    validate_product_url,
)
from app.services.smart_catalog_refresh_v218_service import smart_refresh_product
from app.services.ingestion_observability_v224_service import (
    duplicate_snapshot,
    record_ingestion_result,
)
from app.services.price_integrity_v219_service import (
    audit_product_prices,
    get_price_integrity_status,
)
from app.services.store_offer_reliability_v226_service import (
    audit_product_offer_reliability,
)
from app.services.canonical_alias_reliability_v227_service import (
    converge_exact_identity_aliases_by_source,
)
from app.services.store_retry_intelligence_v2360 import (
    store_retry_intelligence_v2360,
    summarize_store_retry_intelligence_v2360,
)
from app.services.store_retry_scheduler_v2361 import (
    retry_context_key_v2361,
    record_store_attempt_v2361,
    retry_scheduler_snapshot_v2361,
)
from app.services.workload_priority_v23612 import (
    mark_user_deep_queued_v23612,
    mark_user_deep_running_v23612,
    mark_user_deep_done_v23612,
    user_deep_priority_active_v23612,
    user_deep_priority_snapshot_v23612,
)

_ENGINE = "FIRSATAI_PRODUCTION_PRODUCT_INGESTION_PIPELINE"
_VERSION = "23.8.0"
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="v2316-ingestion")
_deep_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="v2316-deep-refresh")
_tasks: dict[str, dict[str, Any]] = {}
_lock = RLock()
_FAST_STORE_TIER = {"pazarama", "teknosa", "mediamarkt", "n11", "vatan"}
# V23.17: user-facing READY waits only for the two fastest high-yield stores.
# The remaining fast tier + slow stores are completed by the existing background deep refresh.
_EARLY_READY_STORE_TIER = {"pazarama", "teknosa"}


def _classify_store_failure_v2347(message: str) -> str:
    text = str(message or "").upper()
    if "SECURITY_CHALLENGE" in text: return "SECURITY_CHALLENGE"
    if "NO_BUYABLE_OFFER" in text: return "NO_BUYABLE_OFFER"
    if "ÜRÜN ADAYI BULUNAMADI" in text or "ADAY_YOK" in text: return "NO_CANDIDATE"
    if "GÜVENLİ EŞLEŞME" in text or "EŞLEŞMESİ BULUNAMADI" in text or "RENK FARKLI" in text or "KESİN RED" in text: return "IDENTITY_REJECT"
    if "FİYAT" in text and ("BULUNAMADI" in text or "HATA" in text): return "PRICE_READ_ERROR"
    if "TIMEOUT" in text or "ZAMAN AŞIM" in text: return "TIMEOUT"
    if "HATA" in text or "ERROR" in text or "EXCEPTION" in text: return "SCRAPE_ERROR"
    return "OTHER"

V2351_TELEMETRY_BASE_PRIORITY = {
    "trendyol": 100, "pazarama": 95, "vatan": 90, "turkcellpasaj": 89, "pttavm": 86, "beymen": 85, "mediamarkt": 88,
    "n11": 84, "hepsiburada": 75, "amazon": 72, "idefix": 47,
    "itopya": 29, "incehesap": 24, "gaminggen": 20,
}

def _scheduler_search_path_v2351(store_code: str) -> str:
    return (
        "HTTP_FIRST_WITH_BROWSER_FALLBACK"
        if str(store_code or "").casefold() in {"gaminggen", "itopya", "incehesap"}
        else "BROWSER_SEARCH"
    )

def _deep_refresh_store_telemetry_v2347(store_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out=[]
    for row in store_results:
        success=bool(row.get("success"))
        raw_message=str(row.get("message") or "")
        url=row.get("product_url")
        score=row.get("match_score")
        scheduler_skipped = bool(row.get("scheduler_skipped"))
        failure_class = (
            "SCHEDULER_SKIP"
            if scheduler_skipped
            else (None if success else _classify_store_failure_v2347(raw_message))
        )
        retry_intel = (
            {
                "reliability_score": row.get("scheduler_skip_reliability_score"),
                "retryable": True,
                "retry_mode": row.get("scheduler_skip_retry_mode"),
                "retry_after_seconds": row.get("scheduler_skip_remaining_seconds"),
                "recommended_action": row.get("scheduler_skip_recommended_action"),
                "reason": row.get("scheduler_skip_reason"),
            }
            if scheduler_skipped
            else store_retry_intelligence_v2360(
                success=success,
                failure_class=failure_class,
            )
        )
        out.append({
            "store_code":row.get("store_code"),
            "store_name":row.get("store_name"),
            "status":"SUCCESS" if success else "FAILED",
            "success":success,
            "duration_seconds":row.get("duration_seconds"),
            "offer_found":bool(success and url),
            "candidate_rejected":bool((not success) and (url or score is not None)),
            "failure_class":failure_class,
            "reliability_score":retry_intel.get("reliability_score"),
            "retryable":retry_intel.get("retryable"),
            "retry_mode":retry_intel.get("retry_mode"),
            "retry_after_seconds":retry_intel.get("retry_after_seconds"),
            "recommended_action":retry_intel.get("recommended_action"),
            "retry_reason":retry_intel.get("reason"),
            "message":"OFFER_SAVED" if success else raw_message,
            "raw_message":raw_message,
            "product_url":url,
            "match_score":score,
            "scheduler_priority":(
                row.get("scheduler_priority")
                if row.get("scheduler_priority") is not None
                else V2351_TELEMETRY_BASE_PRIORITY.get(str(row.get("store_code") or "").casefold(), 50)
            ),
            "scheduler_reason":row.get("scheduler_reason") or "adaptive-category-aware-order-v23.51",
            "search_path":row.get("search_path") or _scheduler_search_path_v2351(str(row.get("store_code") or "")),
            "queue_wait_seconds":row.get("queue_wait_seconds"),
            "execution_seconds":row.get("execution_seconds"),
            "scheduler_wave":row.get("scheduler_wave"),
            "bundle_prefilter_reject_count":int(row.get("bundle_prefilter_reject_count") or 0),
            "bundle_prefilter_reject_samples":list(row.get("bundle_prefilter_reject_samples") or []),
            "scheduler_skipped":scheduler_skipped,
            "scheduler_skip_scope":row.get("scheduler_skip_scope"),
            "scheduler_skip_remaining_seconds":row.get("scheduler_skip_remaining_seconds"),
        })
    return out


def _deep_refresh_queue_wait_v23619(task_id: str) -> float:
    row = get_ingestion_task(task_id) or {}
    queued_at = str(row.get("deep_refresh_queued_at") or "").strip()
    if not queued_at:
        return 0.0
    try:
        queued_dt = datetime.fromisoformat(queued_at)
        return max(0.0, (datetime.utcnow() - queued_dt).total_seconds())
    except Exception:
        return 0.0


def _resubmit_background_deep_refresh_v23619(
    task_id: str,
    global_product_id: int,
    candidate_limit: int,
) -> None:
    # Timer callback yalnızca executor'a yeniden bırakır; kendisi mağaza taramaz.
    try:
        _deep_executor.submit(
            _background_deep_refresh,
            str(task_id),
            int(global_product_id),
            int(candidate_limit),
        )
    except Exception as exc:
        _update(
            task_id,
            deep_refresh_status="FAILED",
            deep_refresh_error=f"{type(exc).__name__}: {exc}",
            deep_refresh_finished_at=datetime.utcnow().isoformat(),
        )


def _defer_background_deep_refresh_v23619(
    task_id: str,
    global_product_id: int,
    candidate_limit: int,
) -> None:
    row = get_ingestion_task(task_id) or {}
    defer_count = int(row.get("deep_refresh_foreground_defer_count") or 0) + 1
    _update(
        task_id,
        deep_refresh_status="QUEUED",
        deep_refresh_priority="BACKGROUND_DEEP_REFRESH",
        deep_refresh_priority_phase="BACKGROUND_DEEP_REFRESH_DEFERRED",
        deep_refresh_queue_reason="FOREGROUND_USER_INGESTION_ACTIVE",
        deep_refresh_queue_wait_seconds=round(_deep_refresh_queue_wait_v23619(task_id), 3),
        deep_refresh_foreground_defer_count=defer_count,
    )
    timer = Timer(
        2.0,
        _resubmit_background_deep_refresh_v23619,
        args=(str(task_id), int(global_product_id), int(candidate_limit)),
    )
    timer.daemon = True
    timer.start()



def _background_deep_refresh(task_id: str, global_product_id: int, candidate_limit: int) -> None:
    """READY sonrası deep refresh artık foreground değil, preemptible background continuation."""
    # V23.61.9: yeni/aktif foreground kullanıcı ingestion varsa worker'ı uzun taramayla
    # işgal etme; hızlıca kuyruğa geri bırak.
    if user_deep_priority_active_v23612():
        print(
            "V23.61.9 DEEP REFRESH DEFER:",
            f"task={task_id}",
            "reason=FOREGROUND_USER_INGESTION_ACTIVE",
        )
        _defer_background_deep_refresh_v23619(
            str(task_id),
            int(global_product_id),
            int(candidate_limit),
        )
        return

    started_perf = perf_counter()
    queue_wait_v23619 = _deep_refresh_queue_wait_v23619(str(task_id))
    _update(
        task_id,
        deep_refresh_status="RUNNING",
        deep_refresh_started_at=datetime.utcnow().isoformat(),
        deep_refresh_queue_reason="DEEP_REFRESH_EXECUTOR_WAIT",
        deep_refresh_queue_wait_seconds=round(queue_wait_v23619,3),
        deep_refresh_priority="BACKGROUND_DEEP_REFRESH",
        deep_refresh_priority_phase="BACKGROUND_DEEP_REFRESH_RUNNING",
        deep_refresh_error=None,
    )
    try:
        refresh = smart_refresh_product(
            global_product_id=int(global_product_id),
            candidate_limit=max(5, min(int(candidate_limit), 50)),
            parallel_workers=4,
            force=False,
            allowed_store_codes=None,
            fast_mode=False,
            workload_class="BACKGROUND_DEEP_REFRESH",
        )

        db = SessionLocal()
        try:
            audit = audit_product_prices(
                db=db,
                global_product_id=int(global_product_id),
            )
            offer_reliability = audit_product_offer_reliability(
                db=db,
                global_product_id=int(global_product_id),
            )
            db.commit()
            serving = get_price_integrity_status(
                db=db,
                global_product_id=int(global_product_id),
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        store_results = list(refresh.get("store_results") or [])
        store_telemetry = _deep_refresh_store_telemetry_v2347(store_results)
        failure_breakdown: dict[str, int] = {}
        for row in store_telemetry:
            fc=row.get("failure_class")
            if fc: failure_breakdown[str(fc)] = failure_breakdown.get(str(fc),0)+1

        source_name_v2361 = str(refresh.get("source_product_name") or "")
        search_query_v2361 = str(refresh.get("search_query") or source_name_v2361)
        context_key_v2361 = retry_context_key_v2361(search_query_v2361, source_name_v2361)
        for row_v2361 in store_telemetry:
            if bool(row_v2361.get("scheduler_skipped")):
                continue
            record_store_attempt_v2361(
                store_code=str(row_v2361.get("store_code") or ""),
                context_key=context_key_v2361,
                success=bool(row_v2361.get("success")),
                failure_class=row_v2361.get("failure_class"),
            )

        retry_summary_v2360 = summarize_store_retry_intelligence_v2360(store_telemetry)
        _background_final_integrity_audit_v236110(
            str(task_id),
            int(global_product_id),
        )
        _update(
            task_id,
            deep_refresh_status="COMPLETED",
            deep_refresh_finished_at=datetime.utcnow().isoformat(),
            deep_refresh_duration_seconds=round(perf_counter() - started_perf, 3),
            deep_refresh_scanned_store_count=int(refresh.get("scanned_store_count", 0) or 0),
            deep_refresh_skipped_store_count=int(refresh.get("skipped_store_count", 0) or 0),
            deep_refresh_smart_backoff_skipped_store_count=len(list(refresh.get("skipped_stores") or [])),
            deep_refresh_smart_backoff_skipped_store_codes=[
                str(row.get("store_code") or "")
                for row in list(refresh.get("skipped_stores") or [])
            ],
            deep_refresh_smart_backoff_skip_details=list(refresh.get("skipped_stores") or []),
            deep_refresh_newly_saved_offer_count=int(refresh.get("newly_saved_offer_count", 0) or 0),
            deep_refresh_store_success_count=sum(1 for row in store_results if bool(row.get("success"))),
            deep_refresh_store_failure_count=sum(1 for row in store_results if not bool(row.get("success"))),
            deep_refresh_store_telemetry_count=len(store_telemetry),
            deep_refresh_total_queue_wait_seconds=round(sum(float(row.get("queue_wait_seconds") or 0.0) for row in store_telemetry), 3),
            deep_refresh_total_execution_seconds=round(sum(float(row.get("execution_seconds") or 0.0) for row in store_telemetry), 3),
            deep_refresh_wave_count=max([int(row.get("scheduler_wave") or 0) for row in store_telemetry] or [0]),
            deep_refresh_bundle_prefilter_reject_count=sum(int(row.get("bundle_prefilter_reject_count") or 0) for row in store_telemetry),
            deep_refresh_bundle_prefilter_store_codes=[str(row.get("store_code") or "") for row in store_telemetry if int(row.get("bundle_prefilter_reject_count") or 0) > 0],
            deep_refresh_bundle_prefilter_reject_samples=[{"store_code": str(row.get("store_code") or ""), **sample} for row in store_telemetry for sample in list(row.get("bundle_prefilter_reject_samples") or [])[:3]][:20],
            deep_refresh_success_store_codes=[
                str(row.get("store_code") or "")
                for row in store_telemetry
                if bool(row.get("success"))
            ],
            deep_refresh_failure_store_codes=[
                str(row.get("store_code") or "")
                for row in store_telemetry
                if not bool(row.get("success"))
            ],
            deep_refresh_store_telemetry=store_telemetry,
            deep_refresh_failure_breakdown=failure_breakdown,
            deep_refresh_retryable_store_count=int(retry_summary_v2360.get("retryable_count") or 0),
            deep_refresh_retryable_store_codes=list(retry_summary_v2360.get("retryable_store_codes") or []),
            deep_refresh_transient_retry_store_codes=list(retry_summary_v2360.get("transient_retry_store_codes") or []),
            deep_refresh_deferred_retry_store_codes=list(retry_summary_v2360.get("deferred_retry_store_codes") or []),
            deep_refresh_context_change_only_store_codes=list(retry_summary_v2360.get("context_change_only_store_codes") or []),
            deep_refresh_scheduler_skipped_store_count=sum(1 for row in store_telemetry if bool(row.get("scheduler_skipped"))),
            deep_refresh_scheduler_skipped_store_codes=[
                str(row.get("store_code") or "")
                for row in store_telemetry
                if bool(row.get("scheduler_skipped"))
            ],
            deep_refresh_scheduler_skip_details=[
                {
                    "store_code": str(row.get("store_code") or ""),
                    "retry_mode": row.get("retry_mode"),
                    "remaining_seconds": row.get("scheduler_skip_remaining_seconds"),
                    "scope": row.get("scheduler_skip_scope"),
                    "reason": row.get("retry_reason"),
                }
                for row in store_telemetry
                if bool(row.get("scheduler_skipped"))
            ],
            deep_refresh_retry_scheduler_state=retry_scheduler_snapshot_v2361(),
            deep_refresh_average_reliability_score=retry_summary_v2360.get("average_reliability_score"),
            deep_refresh_lowest_reliability_store=retry_summary_v2360.get("lowest_reliability_store"),
            deep_refresh_slowest_store=max(store_telemetry,key=lambda row: float(row.get("duration_seconds") or 0.0),default=None),
            deep_refresh=refresh,
            deep_refresh_price_integrity=audit,
            deep_refresh_store_offer_reliability=offer_reliability,
            serving=serving,
            served_best_price=serving.get("served_best_price"),
            served_highest_price=serving.get("served_highest_price"),
            served_offer_count=int(serving.get("served_offer_count", 0) or 0),
            served_store_count=int(serving.get("served_store_count", 0) or 0),
            served_store_codes=list(serving.get("served_store_codes", []) or []),
            quarantined_offer_count=int(serving.get("quarantined_offer_count", 0) or 0),
        )
        final_row = get_ingestion_task(task_id)
        if final_row:
            record_ingestion_result(final_row)
        print(
            "V23.47 background deep refresh telemetry tamamlandı:",
            f"task={task_id}",
            f"global={global_product_id}",
            f"served={serving.get('served_offer_count')}",
            f"stores={serving.get('served_store_count')}",
            f"best={serving.get('served_best_price')}",
        )
    except Exception as exc:
        _update(
            task_id,
            deep_refresh_status="FAILED",
            deep_refresh_finished_at=datetime.utcnow().isoformat(),
            deep_refresh_duration_seconds=round(perf_counter() - started_perf, 3),
            deep_refresh_error=f"{type(exc).__name__}: {exc}",
        )
        final_row = get_ingestion_task(task_id)
        if final_row:
            record_ingestion_result(final_row)
        print("V23.47 background deep refresh başarısız:", type(exc).__name__, exc)
    finally:
        _update(
            task_id,
            deep_refresh_priority_phase="BACKGROUND_DEEP_REFRESH_FINISHED",
            deep_refresh_priority_snapshot=user_deep_priority_snapshot_v23612(),
        )



def _update(task_id: str, **changes: Any) -> None:
    with _lock:
        row = _tasks.get(task_id)
        if row is not None:
            row.update(changes)
            row["updated_at"] = datetime.utcnow().isoformat()


def get_ingestion_task(task_id: str) -> dict[str, Any] | None:
    with _lock:
        row = _tasks.get(str(task_id or ""))
        return dict(row) if row else None


def _resolve_global_product(product: Any) -> tuple[int, dict[str, Any]]:
    identity = ProductIdentityService.explain(product)
    identity_key = str(identity.get("identity_key") or "").strip()
    if not identity_key:
        raise RuntimeError("Canonical identity üretilemedi.")
    db = SessionLocal()
    try:
        gp = (
            db.query(GlobalProduct)
            .filter(GlobalProduct.identity_key == identity_key)
            .first()
        )
        if gp is None:
            raise RuntimeError(
                "Kaynak ürün kaydedildi ancak GlobalProduct bulunamadı: "
                + identity_key
            )
        return int(gp.id), identity
    finally:
        db.close()


def ingest_source_product(url: str) -> dict[str, Any]:
    """Kaynak URL'yi canonical kataloğa kaydeder; mağaza genişletmesini burada başlatmaz."""
    cleaned = str(url or "").strip()
    ok, message = validate_product_url(cleaned)
    if not ok:
        raise ValueError(message)

    registry = get_scraper_registry()
    store = registry.detect_store(cleaned)
    product = registry.scrape(cleaned)
    if product is None:
        raise RuntimeError(f"{store.name} scraper ürün bilgisi döndürmedi.")

    # v22 kendi kontrollü smart-refresh zincirini çalıştırır.
    # save_product içindeki legacy V14.9 otomatik repair bu çağrıda kapalıdır.
    save_product(product, enqueue_repair=False)
    global_product_id, identity = _resolve_global_product(product)

    # V22.7: Geçmiş sürüm hash/key değişimlerinden veya veri-devamlılığı
    # snapshotlarından kalmış aynı identity_source aliaslarını, mağaza
    # discovery başlamadan önce tek GlobalProduct/ProductGroup altında topla.
    alias_audit = converge_exact_identity_aliases_by_source(
        str(identity.get("identity_source") or "")
    )
    canonical_target_id = alias_audit.get("target_global_product_id")
    if canonical_target_id is not None:
        global_product_id = int(canonical_target_id)

    db = SessionLocal()
    try:
        integrity = audit_product_prices(
            db=db,
            global_product_id=global_product_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "success": True,
        "stage": "SOURCE_SAVED",
        "store_code": store.code,
        "store_name": store.name,
        "global_product_id": global_product_id,
        "identity_key": identity.get("identity_key"),
        "identity_source": identity.get("identity_source"),
        "canonical_identity": {
            key: identity.get(key)
            for key in ("brand", "family", "model", "variant", "ram_gb", "storage_gb")
            if identity.get(key) is not None
        },
        "source_price_integrity": integrity,
        "canonical_alias_audit": alias_audit,
        "product": asdict(product),
    }



def _foreground_serving_snapshot_v236110(global_product_id: int) -> dict[str, Any]:
    """READY yolunda yalnız read-only serving snapshot; SQLite writer lock üretmez."""
    db = SessionLocal()
    try:
        return get_price_integrity_status(
            db=db,
            global_product_id=int(global_product_id),
        )
    finally:
        db.close()


def _background_final_integrity_audit_v236110(
    task_id: str,
    global_product_id: int,
) -> None:
    """Mutating final hardening READY sonrasında background çalışır."""
    audit_started = perf_counter()
    _update(
        task_id,
        post_ready_audit_status="RUNNING",
        post_ready_audit_started_at=datetime.utcnow().isoformat(),
    )
    db = SessionLocal()
    try:
        audit = audit_product_prices(
            db=db,
            global_product_id=int(global_product_id),
        )
        reliability = audit_product_offer_reliability(
            db=db,
            global_product_id=int(global_product_id),
        )
        db.commit()
        serving = get_price_integrity_status(
            db=db,
            global_product_id=int(global_product_id),
        )
        _update(
            task_id,
            post_ready_audit_status="COMPLETED",
            post_ready_audit_duration_seconds=round(perf_counter()-audit_started,3),
            post_ready_price_integrity=audit,
            post_ready_offer_reliability=reliability,
            serving=serving,
            served_best_price=serving.get("served_best_price"),
            served_highest_price=serving.get("served_highest_price"),
            served_offer_count=int(serving.get("served_offer_count",0) or 0),
            served_store_count=int(serving.get("served_store_count",0) or 0),
            served_store_codes=list(serving.get("served_store_codes",[]) or []),
            quarantined_offer_count=int(serving.get("quarantined_offer_count",0) or 0),
            post_ready_audit_finished_at=datetime.utcnow().isoformat(),
        )
    except Exception as exc:
        db.rollback()
        _update(
            task_id,
            post_ready_audit_status="FAILED",
            post_ready_audit_error=f"{type(exc).__name__}: {exc}",
            post_ready_audit_duration_seconds=round(perf_counter()-audit_started,3),
            post_ready_audit_finished_at=datetime.utcnow().isoformat(),
        )
    finally:
        db.close()



def _complete_task(
    task_id: str,
    global_product_id: int,
    candidate_limit: int,
    parallel_workers: int,
    pipeline_started_perf: float,
    fast_ingest: bool,
) -> None:
    discovery_started = perf_counter()
    _update(
        task_id,
        status="RUNNING",
        stage="STORE_DISCOVERY",
        started_at=datetime.utcnow().isoformat(),
        deep_refresh_priority_phase="PRIMARY_TIER_RUNNING",
    )
    try:
        refresh = smart_refresh_product(
            global_product_id=global_product_id,
            candidate_limit=candidate_limit,
            parallel_workers=6 if fast_ingest else parallel_workers,
            force=False,
            allowed_store_codes=_EARLY_READY_STORE_TIER if fast_ingest else None,
            fast_mode=bool(fast_ingest),
            workload_class="USER_INGESTION",
        )
        discovery_duration = round(perf_counter() - discovery_started, 3)
        _update(
            task_id,
            stage="READY_SNAPSHOT",
            discovery_duration_seconds=discovery_duration,
            foreground_finalization_policy="READ_ONLY_NO_SQLITE_WRITER",
        )
        integrity_started = perf_counter()
        status = _foreground_serving_snapshot_v236110(global_product_id)
        audit = {
            "deferred": True,
            "policy": "POST_READY_BACKGROUND_FINAL_AUDIT",
        }
        offer_reliability = {
            "deferred": True,
            "policy": "POST_READY_BACKGROUND_FINAL_AUDIT",
            "status": {
                "active_global_offer_count": int(status.get("served_offer_count",0) or 0),
                "active_store_count": int(status.get("served_store_count",0) or 0),
                "active_store_codes": list(status.get("served_store_codes",[]) or []),
            },
        }
        integrity_duration = round(perf_counter() - integrity_started, 3)
        total_duration = round(perf_counter() - pipeline_started_perf, 3)
        identity_key = str((get_ingestion_task(task_id) or {}).get("identity_key") or "")
        duplicate = duplicate_snapshot(identity_key, global_product_id)
        store_results = list(refresh.get("store_results") or [])
        store_success_count = sum(1 for row in store_results if bool(row.get("success")))
        store_failure_count = len(store_results) - store_success_count
        quarantined = int(status.get("quarantined_offer_count", 0) or 0)
        print(
            "V23.61.10 foreground READY snapshot:",
            f"global={global_product_id}",
            f"kind={status.get('product_kind')}",
            f"served_best={status.get('served_best_price')}",
            f"served={status.get('served_offer_count')}",
            f"quarantine={status.get('quarantined_offer_count')}",
        )
        metrics = {
            "duration_seconds": total_duration,
            "ready_policy": "PRIMARY_TIER_THEN_BACKGROUND" if fast_ingest else "FULL_SCAN",
            "early_ready_store_codes": sorted(_EARLY_READY_STORE_TIER) if fast_ingest else [],
            "discovery_duration_seconds": discovery_duration,
            "price_integrity_duration_seconds": integrity_duration,
            "scanned_store_count": int(refresh.get("scanned_store_count", 0) or 0),
            "skipped_store_count": int(refresh.get("skipped_store_count", 0) or 0),
            "store_success_count": store_success_count,
            "store_failure_count": store_failure_count,
            "newly_saved_offer_count": int(refresh.get("newly_saved_offer_count", 0) or 0),
            "active_offer_count": int(
                offer_reliability.get("status", {}).get("active_global_offer_count", 0) or 0
            ),
            "active_store_count": int(
                offer_reliability.get("status", {}).get("active_store_count", 0) or 0
            ),
            "active_store_codes": list(
                offer_reliability.get("status", {}).get("active_store_codes", []) or []
            ),
            "quarantined_offer_count": quarantined,
            "served_best_price": status.get("served_best_price"),
            "served_highest_price": status.get("served_highest_price"),
            "served_offer_count": int(status.get("served_offer_count", 0) or 0),
            "served_store_count": int(status.get("served_store_count", 0) or 0),
            "served_store_codes": list(status.get("served_store_codes", []) or []),
            "store_results": store_results,
            **duplicate,
        }
        _update(
            task_id,
            status="COMPLETED",
            stage="READY",
            refresh=refresh,
            price_integrity=audit,
            serving=status,
            store_offer_reliability=offer_reliability,
            post_ready_audit_status="QUEUED",
            foreground_ready_at=datetime.utcnow().isoformat(),
            finished_at=datetime.utcnow().isoformat(),
            **metrics,
        )
        if fast_ingest:
            # V23.61.9: foreground priority yalnız READY'ye kadardır.
            # READY sonrası zenginleştirme background continuation'dır.
            mark_user_deep_done_v23612(str(task_id))
            _update(
                task_id,
                deep_refresh_status="QUEUED",
                deep_refresh_queued_at=datetime.utcnow().isoformat(),
                fast_ingest=True,
                deferred_store_codes=sorted(_FAST_STORE_TIER - _EARLY_READY_STORE_TIER),
                deep_refresh_priority="BACKGROUND_DEEP_REFRESH",
                deep_refresh_priority_phase="BACKGROUND_DEEP_REFRESH_QUEUED",
                deep_refresh_queue_reason="DEEP_REFRESH_EXECUTOR_WAIT",
                deep_refresh_priority_snapshot=user_deep_priority_snapshot_v23612(),
            )
            _deep_executor.submit(
                _background_deep_refresh,
                str(task_id),
                int(global_product_id),
                int(candidate_limit),
            )
        else:
            mark_user_deep_done_v23612(str(task_id))
            _update(
                task_id,
                deep_refresh_priority_phase="FULL_SCAN_COMPLETED",
                deep_refresh_priority_snapshot=user_deep_priority_snapshot_v23612(),
            )
        final_row = get_ingestion_task(task_id)
        if final_row:
            record_ingestion_result(final_row)
    except Exception as exc:
        total_duration = round(perf_counter() - pipeline_started_perf, 3)
        _update(
            task_id,
            status="FAILED",
            stage="FAILED",
            duration_seconds=total_duration,
            error=f"{type(exc).__name__}: {exc}",
            finished_at=datetime.utcnow().isoformat(),
        )
        mark_user_deep_done_v23612(str(task_id))
        final_row = get_ingestion_task(task_id)
        if final_row:
            record_ingestion_result(final_row)


def start_production_ingestion(
    *,
    url: str,
    candidate_limit: int = 50,
    parallel_workers: int = 6,
    fast_ingest: bool = True,
) -> dict[str, Any]:
    pipeline_started_perf = perf_counter()
    source_started = perf_counter()
    task_id = uuid4().hex

    # V23.61.3: kullanıcı priority lease'i POST kabul edildiği anda açılır.
    # Böylece source scrape + primary-tier süresince background catalog yeni
    # ürün/batch başlatamaz.
    mark_user_deep_queued_v23612(str(task_id))

    try:
        source = ingest_source_product(url)
    except Exception as exc:
        source_duration = round(perf_counter() - source_started, 3)
        failed_row = {
            "engine": _ENGINE,
            "engine_version": _VERSION,
            "task_id": task_id,
            "status": "FAILED",
            "stage": "SOURCE_FAILED",
            "url": str(url or ""),
            "source_duration_seconds": source_duration,
            "duration_seconds": round(perf_counter() - pipeline_started_perf, 3),
            "error": f"{type(exc).__name__}: {exc}",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "finished_at": datetime.utcnow().isoformat(),
        }
        with _lock:
            _tasks[task_id] = failed_row
        mark_user_deep_done_v23612(str(task_id))
        record_ingestion_result(failed_row)
        raise
    source_duration = round(perf_counter() - source_started, 3)
    row = {
        "engine": _ENGINE,
        "engine_version": _VERSION,
        "task_id": task_id,
        "status": "QUEUED",
        "stage": "SOURCE_SAVED",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "source_duration_seconds": source_duration,
        "category": str((source.get("product") or {}).get("category") or "UNKNOWN"),
        "fast_ingest": bool(fast_ingest),
        "ingestion_mode": "FAST" if fast_ingest else "FULL",
        "deep_refresh_priority": "USER_INGESTION",
        "deep_refresh_priority_phase": "SOURCE_SAVED_PRIMARY_PENDING",
        "deep_refresh_priority_snapshot": user_deep_priority_snapshot_v23612(),
        **source,
    }
    with _lock:
        _tasks[task_id] = row

    _executor.submit(
        _complete_task,
        task_id,
        int(source["global_product_id"]),
        int(candidate_limit),
        int(parallel_workers),
        pipeline_started_perf,
        bool(fast_ingest),
    )
    return dict(row)


def runtime_info() -> dict[str, Any]:
    return {
        "engine": _ENGINE,
        "engine_version": _VERSION,
        "pipeline": [
            "SOURCE_SCRAPE",
            "CANONICAL_IDENTITY",
            "GLOBAL_PRODUCT_UPSERT",
            "SOURCE_OFFER_PRICE_INTEGRITY",
            "SMART_STORE_DISCOVERY",
            "STRICT_MATCHING",
            "GLOBAL_OFFER_UPSERT",
            "FINAL_PRICE_INTEGRITY",
            "READY",
        ],
        "legacy_auto_repair_during_source_save": False,
        "background_store_discovery": True,
        "observability": "v22.4-persistent-metrics",
    }
