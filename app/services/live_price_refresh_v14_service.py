from __future__ import annotations

import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, RawProduct
from app.services.global_price_history_service import record_global_offer_price
from app.services.scraper_registry import ScraperRegistry


_lock = threading.RLock()
_tasks: dict[str, dict[str, Any]] = {}
_active_task_id: str | None = None


def _utcnow() -> datetime:
    return datetime.utcnow()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _money(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 2) if number > 0 else None


def _snapshot(task: dict[str, Any]) -> dict[str, Any]:
    safe = dict(task)
    safe["items"] = [dict(x) for x in task.get("items", [])[-100:]]
    return safe


def get_live_price_status(task_id: str | None = None) -> dict[str, Any]:
    with _lock:
        selected = task_id or _active_task_id
        if not selected or selected not in _tasks:
            return {
                "engine_version": "14.6.0",
                "status": "IDLE",
                "active_task_id": None,
                "task": None,
            }
        return {
            "engine_version": "14.6.0",
            "status": _tasks[selected]["status"],
            "active_task_id": selected,
            "task": _snapshot(_tasks[selected]),
        }


def list_refreshable_offers(
    *,
    limit: int = 100,
    store_code: str | None = None,
) -> list[int]:
    db = SessionLocal()
    try:
        query = (
            db.query(GlobalOffer.id)
            .filter(
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
                GlobalOffer.url.isnot(None),
                GlobalOffer.url != "",
            )
        )
        if store_code:
            query = query.filter(GlobalOffer.store_code == store_code)
        rows = (
            query.order_by(
                GlobalOffer.last_seen_at.asc(),
                GlobalOffer.id.asc(),
            )
            .limit(max(1, min(int(limit), 2000)))
            .all()
        )
        return [int(row[0]) for row in rows]
    finally:
        db.close()


def _refresh_one_offer(
    *,
    offer_id: int,
    retry_count: int,
) -> dict[str, Any]:
    started = time.monotonic()
    last_error: Exception | None = None

    for attempt in range(1, max(1, retry_count) + 1):
        db = SessionLocal()
        try:
            offer = db.query(GlobalOffer).filter(GlobalOffer.id == offer_id).first()
            if offer is None:
                return {
                    "offer_id": offer_id,
                    "status": "SKIPPED",
                    "message": "Teklif bulunamadı.",
                    "duration_seconds": round(time.monotonic() - started, 2),
                }

            old_price = _money(offer.current_price)
            old_stock = str(offer.availability or "")
            url = str(offer.url or "").strip()
            if not url:
                return {
                    "offer_id": offer_id,
                    "store_code": offer.store_code,
                    "status": "SKIPPED",
                    "message": "Teklif URL'si boş.",
                    "duration_seconds": round(time.monotonic() - started, 2),
                }

            registry = ScraperRegistry()
            product = registry.scrape(url)
            new_price = _money(getattr(product, "price", None))
            if new_price is None:
                raise ValueError("Scraper geçerli fiyat döndürmedi.")

            new_stock = str(getattr(product, "stock_status", None) or old_stock)
            new_old_price = _money(getattr(product, "old_price", None))
            new_shipping = _money(getattr(product, "shipping_price", None))
            checked_at = _utcnow()

            price_changed = old_price != new_price
            stock_changed = old_stock != new_stock

            offer.old_price = old_price if price_changed else (new_old_price or offer.old_price)
            offer.current_price = new_price
            if new_shipping is not None:
                offer.shipping_price = new_shipping
            offer.availability = new_stock
            offer.seller = getattr(product, "seller", None) or offer.seller
            offer.delivery_text = getattr(product, "delivery_text", None) or offer.delivery_text
            offer.warranty_type = getattr(product, "warranty_type", None) or offer.warranty_type
            offer.campaign_text = getattr(product, "campaign_text", None) or offer.campaign_text
            offer.installment_text = getattr(product, "installment_text", None) or offer.installment_text
            official = getattr(product, "is_official_seller", None)
            if official is not None:
                offer.is_official_seller = bool(official)
            offer.last_seen_at = checked_at
            offer.updated_at = checked_at
            offer.lifecycle_status = "ACTIVE"
            offer.is_active = True

            raw = db.query(RawProduct).filter(RawProduct.id == offer.raw_product_id).first()
            if raw is not None:
                raw.price_raw = new_price
                raw.old_price_raw = new_old_price
                raw.stock_raw = new_stock
                raw.seller_raw = getattr(product, "seller", None) or raw.seller_raw
                raw.title_raw = getattr(product, "name", None) or raw.title_raw
                raw.image_raw = getattr(product, "image", None) or raw.image_raw
                raw.last_seen_at = checked_at
                raw.updated_at = checked_at

            db.flush()
            history = None
            if price_changed or stock_changed:
                history = record_global_offer_price(
                    db=db,
                    offer=offer,
                    checked_at=checked_at,
                    force=True,
                )

            db.commit()
            change_percent = None
            if price_changed and old_price:
                change_percent = round((new_price - old_price) / old_price * 100, 2)

            return {
                "offer_id": offer.id,
                "global_product_id": offer.global_product_id,
                "store_code": offer.store_code,
                "status": "CHANGED" if (price_changed or stock_changed) else "UNCHANGED",
                "old_price": old_price,
                "new_price": new_price,
                "change_percent": change_percent,
                "old_stock": old_stock,
                "new_stock": new_stock,
                "history_written": history is not None,
                "attempt": attempt,
                "duration_seconds": round(time.monotonic() - started, 2),
            }
        except Exception as exc:
            db.rollback()
            last_error = exc
        finally:
            db.close()

        if attempt < retry_count:
            time.sleep(min(2 * attempt, 5))

    return {
        "offer_id": offer_id,
        "status": "FAILED",
        "message": f"{type(last_error).__name__}: {last_error}",
        "traceback": traceback.format_exc(limit=4),
        "attempt": max(1, retry_count),
        "duration_seconds": round(time.monotonic() - started, 2),
    }


def _run_task(
    *,
    task_id: str,
    offer_ids: list[int],
    workers: int,
    retry_count: int,
) -> None:
    global _active_task_id

    with _lock:
        task = _tasks[task_id]
        task["status"] = "RUNNING"
        task["started_at"] = _iso(_utcnow())

    try:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as executor:
            futures = {
                executor.submit(
                    _refresh_one_offer,
                    offer_id=offer_id,
                    retry_count=retry_count,
                ): offer_id
                for offer_id in offer_ids
            }

            for future in as_completed(futures):
                result = future.result()
                with _lock:
                    task = _tasks[task_id]
                    task["processed"] += 1
                    task["progress_percent"] = round(
                        task["processed"] / max(1, task["total"]) * 100,
                        2,
                    )
                    task["items"].append(result)
                    status = result.get("status")
                    if status == "CHANGED":
                        task["changed"] += 1
                    elif status == "UNCHANGED":
                        task["unchanged"] += 1
                    elif status == "SKIPPED":
                        task["skipped"] += 1
                    else:
                        task["failed"] += 1
                    task["message"] = (
                        f"{task['processed']}/{task['total']} teklif kontrol edildi"
                    )

        with _lock:
            task = _tasks[task_id]
            task["status"] = (
                "COMPLETED_WITH_ERRORS" if task["failed"] else "COMPLETED"
            )
            task["finished_at"] = _iso(_utcnow())
            task["progress_percent"] = 100.0
            task["message"] = (
                f"Tamamlandı: {task['changed']} değişti, "
                f"{task['unchanged']} aynı, {task['failed']} başarısız"
            )
    except Exception as exc:
        with _lock:
            task = _tasks[task_id]
            task["status"] = "FAILED"
            task["finished_at"] = _iso(_utcnow())
            task["message"] = f"{type(exc).__name__}: {exc}"
    finally:
        with _lock:
            if _active_task_id == task_id:
                _active_task_id = None


def start_live_price_refresh(
    *,
    limit: int = 100,
    workers: int = 2,
    retry_count: int = 2,
    store_code: str | None = None,
) -> dict[str, Any]:
    global _active_task_id

    with _lock:
        if _active_task_id and _tasks.get(_active_task_id, {}).get("status") in {
            "QUEUED",
            "RUNNING",
        }:
            return {
                "started": False,
                "reason": "ACTIVE_TASK_EXISTS",
                "task": _snapshot(_tasks[_active_task_id]),
            }

    offer_ids = list_refreshable_offers(limit=limit, store_code=store_code)
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "engine_version": "14.6.0",
        "status": "QUEUED",
        "created_at": _iso(_utcnow()),
        "started_at": None,
        "finished_at": None,
        "store_code": store_code,
        "workers": max(1, min(int(workers), 4)),
        "retry_count": max(1, min(int(retry_count), 3)),
        "total": len(offer_ids),
        "processed": 0,
        "changed": 0,
        "unchanged": 0,
        "failed": 0,
        "skipped": 0,
        "progress_percent": 0.0,
        "message": "Görev kuyruğa alındı.",
        "items": [],
    }

    with _lock:
        _tasks[task_id] = task
        _active_task_id = task_id

    if not offer_ids:
        with _lock:
            task["status"] = "COMPLETED"
            task["finished_at"] = _iso(_utcnow())
            task["progress_percent"] = 100.0
            task["message"] = "Kontrol edilecek aktif teklif bulunamadı."
            _active_task_id = None
        return {"started": True, "task": _snapshot(task)}

    thread = threading.Thread(
        target=_run_task,
        kwargs={
            "task_id": task_id,
            "offer_ids": offer_ids,
            "workers": task["workers"],
            "retry_count": task["retry_count"],
        },
        daemon=True,
        name=f"live-price-refresh-{task_id[:8]}",
    )
    thread.start()
    return {"started": True, "task": _snapshot(task)}


def live_price_summary() -> dict[str, Any]:
    db = SessionLocal()
    try:
        offers = (
            db.query(GlobalOffer)
            .filter(
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
            )
            .all()
        )
        store_counts: dict[str, int] = {}
        for offer in offers:
            store_counts[offer.store_code] = store_counts.get(offer.store_code, 0) + 1
        return {
            "engine_version": "14.6.0",
            "status": "LIVE_PRICE_ENGINE_READY",
            "active_offer_count": len(offers),
            "store_counts": store_counts,
            "task_status": get_live_price_status(),
        }
    finally:
        db.close()
