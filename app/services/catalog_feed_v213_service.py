from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct
from app.services.multi_store_offer_repair_v14_service import (
    product_from_global_product,
    repair_product_across_stores,
)
from app.services.workload_priority_v23612 import user_deep_priority_active_v23612, user_priority_generation_v23617


_lock = threading.RLock()
_feed_task: asyncio.Task[Any] | None = None
_stop_event: asyncio.Event | None = None

_state: dict[str, Any] = {
    "status": "IDLE",
    "last_started_at": None,
    "last_finished_at": None,
    "last_error": None,
    "run_count": 0,
    "product_count": 0,
    "successful_product_count": 0,
    "failed_product_count": 0,
    "newly_saved_offer_count": 0,
    "last_results": [],
}


def _utcnow() -> datetime:
    return datetime.utcnow()


def get_catalog_feed_status() -> dict[str, Any]:
    with _lock:
        data = dict(_state)
        data["last_results"] = [dict(item) for item in _state.get("last_results", [])]
        return data


def _candidate_rows(*, limit: int, stale_hours: int) -> list[dict[str, Any]]:
    """Return products that benefit most from background offer refresh.

    Priority is deliberately catalogue-centric rather than page-request-centric:
    products with no offers, fewer stores, no fresh offers and older sightings go first.
    """
    db = SessionLocal()
    try:
        products = (
            db.query(GlobalProduct)
            .filter(GlobalProduct.status == "ACTIVE")
            .order_by(GlobalProduct.id.asc())
            .limit(1000)
            .all()
        )
        if not products:
            return []

        ids = [int(row.id) for row in products]
        offer_rows = (
            db.query(
                GlobalOffer.global_product_id,
                func.count(GlobalOffer.id),
                func.count(func.distinct(GlobalOffer.store_code)),
                func.max(GlobalOffer.last_seen_at),
            )
            .filter(
                GlobalOffer.global_product_id.in_(ids),
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
            )
            .group_by(GlobalOffer.global_product_id)
            .all()
        )
        aggregate = {
            int(product_id): {
                "offer_count": int(offer_count or 0),
                "store_count": int(store_count or 0),
                "last_seen_at": last_seen_at,
            }
            for product_id, offer_count, store_count, last_seen_at in offer_rows
        }

        fresh_cutoff = _utcnow() - timedelta(hours=max(1, int(stale_hours)))
        fresh_rows = (
            db.query(
                GlobalOffer.global_product_id,
                func.count(func.distinct(GlobalOffer.store_code)),
            )
            .filter(
                GlobalOffer.global_product_id.in_(ids),
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
                GlobalOffer.last_seen_at >= fresh_cutoff,
            )
            .group_by(GlobalOffer.global_product_id)
            .all()
        )
        fresh_store_counts = {int(product_id): int(count or 0) for product_id, count in fresh_rows}

        now = _utcnow()
        candidates: list[dict[str, Any]] = []
        for product in products:
            stats = aggregate.get(int(product.id), {})
            offer_count = int(stats.get("offer_count", 0))
            store_count = int(stats.get("store_count", 0))
            fresh_store_count = int(fresh_store_counts.get(int(product.id), 0))
            last_seen_at = stats.get("last_seen_at")
            age_hours = 9999.0 if last_seen_at is None else max(0.0, (now - last_seen_at).total_seconds() / 3600.0)

            # Prefer products with weak marketplace coverage. A healthy catalogue item
            # with >= 5 fresh stores is not needlessly rescanned every cycle.
            if fresh_store_count >= 5 and age_hours < max(1, stale_hours):
                continue

            priority = 0.0
            if offer_count == 0:
                priority += 10000.0
            priority += max(0, 5 - store_count) * 1000.0
            if fresh_store_count == 0:
                priority += 750.0
            priority += min(age_hours, 720.0)

            candidates.append(
                {
                    "global_product_id": int(product.id),
                    "name": product.canonical_name,
                    "store_count": store_count,
                    "fresh_store_count": fresh_store_count,
                    "offer_count": offer_count,
                    "age_hours": round(age_hours, 2),
                    "priority": round(priority, 2),
                }
            )

        candidates.sort(key=lambda item: (-item["priority"], item["global_product_id"]))
        return candidates[: max(1, min(int(limit), 25))]
    finally:
        db.close()


def run_catalog_feed_once(
    *,
    limit: int = 3,
    stale_hours: int = 6,
    candidate_limit: int = 50,
    parallel_workers: int = 3,
    only_global_product_id: int | None = None,
) -> dict[str, Any]:
    """Refresh a small catalogue batch using the existing protected repair pipeline.

    Identity/matcher/save logic is intentionally reused instead of reimplemented.
    One product/store failure never aborts the remaining catalogue batch.
    """
    started_at = _utcnow()
    with _lock:
        if _state.get("status") == "RUNNING":
            return {"started": False, "reason": "ALREADY_RUNNING", **get_catalog_feed_status()}
        _state.update(
            {
                "status": "RUNNING",
                "last_started_at": started_at.isoformat(),
                "last_finished_at": None,
                "last_error": None,
                "product_count": 0,
                "successful_product_count": 0,
                "failed_product_count": 0,
                "newly_saved_offer_count": 0,
                "last_results": [],
            }
        )

    if only_global_product_id is not None:
        candidates = [
            {
                "global_product_id": int(only_global_product_id),
                "name": None,
                "store_count": None,
                "fresh_store_count": None,
                "offer_count": None,
                "age_hours": None,
                "priority": None,
            }
        ]
    else:
        candidates = _candidate_rows(limit=limit, stale_hours=stale_hours)

    results: list[dict[str, Any]] = []
    successful = 0
    failed = 0
    saved = 0

    try:
        for candidate in candidates:
            product_id = int(candidate["global_product_id"])
            try:
                source_product = product_from_global_product(product_id)
                scan = repair_product_across_stores(
                    source_product=source_product,
                    target_global_product_id=product_id,
                    candidate_limit=max(5, min(int(candidate_limit), 100)),
                    parallel_workers=max(1, min(int(parallel_workers), 6)),
                    workload_class="BACKGROUND",
                )
                successful += 1
                newly_saved = int(scan.get("newly_saved_offer_count", 0) or 0)
                saved += newly_saved
                results.append(
                    {
                        **candidate,
                        "success": True,
                        "searched_store_count": scan.get("searched_store_count", 0),
                        "newly_saved_offer_count": newly_saved,
                        "active_offer_count": scan.get("active_offer_count", 0),
                        "store_count_after": scan.get("store_count", 0),
                        "stores": scan.get("stores", []),
                        "store_results": scan.get("results", []),
                    }
                )
            except Exception as error:
                failed += 1
                results.append(
                    {
                        **candidate,
                        "success": False,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )

        finished_at = _utcnow()
        payload = {
            "started": True,
            "engine": "FIRSATAI_CATALOG_FEED_ENGINE",
            "engine_version": "21.3.0",
            "status": "COMPLETED",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 2),
            "product_count": len(candidates),
            "successful_product_count": successful,
            "failed_product_count": failed,
            "newly_saved_offer_count": saved,
            "results": results,
        }
        with _lock:
            _state.update(
                {
                    "status": "IDLE",
                    "last_finished_at": finished_at.isoformat(),
                    "run_count": int(_state.get("run_count", 0)) + 1,
                    "product_count": len(candidates),
                    "successful_product_count": successful,
                    "failed_product_count": failed,
                    "newly_saved_offer_count": saved,
                    "last_results": results[-10:],
                }
            )
        return payload
    except Exception as error:
        with _lock:
            _state.update(
                {
                    "status": "IDLE",
                    "last_finished_at": _utcnow().isoformat(),
                    "last_error": f"{type(error).__name__}: {error}",
                    "failed_product_count": failed + 1,
                    "last_results": results[-10:],
                }
            )
        raise


async def _feed_loop(*, interval_seconds: int, initial_delay_seconds: int, batch_size: int, stale_hours: int) -> None:
    global _stop_event
    _stop_event = asyncio.Event()
    print(
        "V21.7 akıllı katalog teklif besleme motoru başlatıldı. "
        f"Aralık: {max(1, interval_seconds // 60)} dk, batch: {batch_size}."
    )

    if initial_delay_seconds > 0:
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=initial_delay_seconds)
        except asyncio.TimeoutError:
            pass

    while not _stop_event.is_set():
        try:
            # V21.7: scheduler artık mağaza bazlı backoff kullanan smart refresh
            # çalıştırır. Legacy v213 manuel endpointleri tam tarama için korunur.
            feed_generation_v23617 = user_priority_generation_v23617()
            if user_deep_priority_active_v23612():
                print("V23.61.7 CATALOG FEED YIELD: user-ingestion-priority-active; yeni batch ertelendi.")
            else:
                candidates = await asyncio.to_thread(_candidate_rows, limit=batch_size, stale_hours=stale_hours)
                product_ids = [int(row["global_product_id"]) for row in candidates]

                current_generation_v23617 = user_priority_generation_v23617()
                if current_generation_v23617 != feed_generation_v23617:
                    print(
                        "V23.61.7 CATALOG FEED GENERATION YIELD:",
                        f"before={feed_generation_v23617}",
                        f"after={current_generation_v23617}",
                        f"deferred={product_ids}",
                    )
                elif product_ids:
                    from app.services.smart_catalog_refresh_v218_service import smart_refresh_batch
                    await asyncio.to_thread(smart_refresh_batch, product_ids=product_ids)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print("V21.3 katalog teklif besleme hatası:", error)

        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass

    print("V21.3 katalog teklif besleme motoru durduruldu.")


async def start_catalog_feed(*, enabled: bool, interval_minutes: int, initial_delay_seconds: int, batch_size: int, stale_hours: int) -> None:
    global _feed_task
    if not enabled:
        print("V21.3 katalog teklif besleme motoru devre dışı.")
        return
    if _feed_task is not None and not _feed_task.done():
        return
    _feed_task = asyncio.create_task(
        _feed_loop(
            interval_seconds=max(60, int(interval_minutes) * 60),
            initial_delay_seconds=max(0, int(initial_delay_seconds)),
            batch_size=max(1, min(int(batch_size), 25)),
            stale_hours=max(1, int(stale_hours)),
        ),
        name="catalog-feed-v213",
    )


async def stop_catalog_feed() -> None:
    global _feed_task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    if _feed_task is None:
        return
    try:
        await _feed_task
    except asyncio.CancelledError:
        pass
    finally:
        _feed_task = None
