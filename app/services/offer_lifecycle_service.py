from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from app.database.models import ProductOffer
from app.services.offer_integrity_service import ACTIVE, ARCHIVED, MISSING


@dataclass(frozen=True)
class OfferLifecycleResult:
    checked: int
    marked_missing: int
    deactivated: int


def mark_store_scan_results(db, *, store_id: int, seen_offer_ids: Iterable[int], miss_limit: int = 2) -> OfferLifecycleResult:
    """Tarama sonunda görülmeyen teklifleri güvenli biçimde pasifleştirir.

    Tek taramada görünmeyen teklif hemen silinmez. Art arda ``miss_limit`` kez
    görülmezse pasif olur. Böylece geçici mağaza hataları veri kaybına yol açmaz.
    """
    seen = {int(value) for value in seen_offer_ids}
    rows = db.query(ProductOffer).filter(ProductOffer.store_id == store_id).all()
    now = datetime.utcnow()
    missing = deactivated = 0
    for offer in rows:
        if offer.id in seen:
            offer.is_active = True
            offer.inactive_at = None
            offer.consecutive_misses = 0
            offer.lifecycle_status = ACTIVE
            continue
        missing += 1
        offer.consecutive_misses = int(offer.consecutive_misses or 0) + 1
        offer.lifecycle_status = MISSING
        if offer.consecutive_misses >= max(1, miss_limit):
            offer.is_active = False
            offer.inactive_at = now
            offer.is_best_offer = False
            offer.lifecycle_status = ARCHIVED
            deactivated += 1
    db.flush()
    return OfferLifecycleResult(len(rows), missing, deactivated)


def expire_stale_offers(db, *, max_age_hours: int = 48) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=max(1, max_age_hours))
    rows = (
        db.query(ProductOffer)
        .filter(ProductOffer.is_active.is_(True), ProductOffer.last_checked_at < cutoff)
        .all()
    )
    now = datetime.utcnow()
    for offer in rows:
        offer.is_active = False
        offer.inactive_at = now
        offer.is_best_offer = False
        offer.lifecycle_status = ARCHIVED
    db.flush()
    return len(rows)


def total_price(offer: ProductOffer) -> float:
    return round(float(offer.current_price or 0) + float(offer.shipping_price or 0), 2)
