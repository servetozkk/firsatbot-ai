from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import func

from app.database.models import OfferPriceHistory, ProductOffer
from app.services.multi_store_service import is_offer_available
from app.services.offer_integrity_service import (
    ACTIVE,
    ARCHIVED,
    MISSING,
    OUT_OF_STOCK,
    UPDATED,
    build_dedupe_key,
    normalize_seller,
)


@dataclass(slots=True)
class OfferMaintenanceResult:
    checked: int = 0
    dedupe_keys_filled: int = 0
    duplicates_archived: int = 0
    histories_moved: int = 0
    marked_missing: int = 0
    archived_stale: int = 0
    status_fixed: int = 0
    best_offer_groups_fixed: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def _total_price(offer: ProductOffer) -> float:
    return round(float(offer.current_price or 0) + float(offer.shipping_price or 0), 2)


def _eligible(offer: ProductOffer) -> bool:
    return bool(
        offer.is_active
        and not offer.is_hidden
        and str(offer.lifecycle_status or ACTIVE) in {ACTIVE, UPDATED}
        and float(offer.current_price or 0) > 0
        and is_offer_available(offer.availability)
    )


def _survivor_rank(offer: ProductOffer) -> tuple:
    return (
        1 if offer.is_active else 0,
        1 if not offer.is_hidden else 0,
        offer.last_checked_at or datetime.min,
        offer.updated_at or datetime.min,
        -int(offer.id or 0),
    )


def _compatible_dedupe_key(offer: ProductOffer, normalized_seller: str) -> str:
    """
    Eski ve yeni offer_integrity_service sürümleriyle uyumlu çalışır.

    Bazı sürümlerde build_dedupe_key() normalized_seller parametresini kabul
    ederken, mevcut projede yalnızca seller parametresi kabul edilmektedir.
    """
    common = {
        "store_id": offer.store_id,
        "store_product_id": offer.store_product_id,
        "seller": normalized_seller or offer.seller,
        "url": offer.url,
    }
    try:
        return build_dedupe_key(
            **common,
            normalized_seller=normalized_seller,
        )
    except TypeError as exc:
        if "normalized_seller" not in str(exc):
            raise
        return build_dedupe_key(**common)


def fill_missing_dedupe_keys(db, offers: Iterable[ProductOffer] | None = None) -> int:
    rows = list(offers) if offers is not None else db.query(ProductOffer).all()
    changed = 0

    for offer in rows:
        normalized = normalize_seller(offer.seller)
        key = _compatible_dedupe_key(offer, normalized)

        if offer.normalized_seller != normalized:
            offer.normalized_seller = normalized
            changed += 1

        if not offer.dedupe_key or offer.dedupe_key != key:
            offer.dedupe_key = key
            changed += 1

    db.flush()
    return changed


def archive_duplicate_offers(db) -> tuple[int, int]:
    rows = (
        db.query(ProductOffer)
        .order_by(ProductOffer.store_id.asc(), ProductOffer.id.asc())
        .all()
    )
    fill_missing_dedupe_keys(db, rows)

    buckets: dict[tuple[int, str], list[ProductOffer]] = defaultdict(list)
    for offer in rows:
        if offer.dedupe_key:
            buckets[(int(offer.store_id), str(offer.dedupe_key))].append(offer)

    archived = 0
    moved = 0
    now = datetime.utcnow()

    for bucket in buckets.values():
        if len(bucket) < 2:
            continue

        survivor = max(bucket, key=_survivor_rank)
        duplicates = [item for item in bucket if item.id != survivor.id]

        for duplicate in duplicates:
            histories = (
                db.query(OfferPriceHistory)
                .filter(OfferPriceHistory.offer_id == duplicate.id)
                .order_by(OfferPriceHistory.created_at.asc())
                .all()
            )
            existing_history = {
                (round(float(item.price or 0), 2), item.created_at)
                for item in db.query(OfferPriceHistory)
                .filter(OfferPriceHistory.offer_id == survivor.id)
                .all()
            }

            for history in histories:
                signature = (round(float(history.price or 0), 2), history.created_at)
                if signature in existing_history:
                    db.delete(history)
                else:
                    history.offer_id = survivor.id
                    existing_history.add(signature)
                    moved += 1

            duplicate.is_active = False
            duplicate.is_hidden = True
            duplicate.is_best_offer = False
            duplicate.lifecycle_status = ARCHIVED
            duplicate.inactive_at = duplicate.inactive_at or now

            note = str(duplicate.admin_note or "").strip()
            marker = f"Tekrar teklif; ana teklif #{survivor.id}"
            duplicate.admin_note = f"{note} | {marker}".strip(" |")
            archived += 1

            if (duplicate.last_checked_at or datetime.min) > (
                survivor.last_checked_at or datetime.min
            ):
                survivor.current_price = duplicate.current_price
                survivor.old_price = duplicate.old_price or survivor.old_price
                survivor.shipping_price = duplicate.shipping_price
                survivor.availability = duplicate.availability
                survivor.rating = duplicate.rating
                survivor.review_count = duplicate.review_count
                survivor.last_checked_at = duplicate.last_checked_at
                survivor.updated_at = duplicate.updated_at
                survivor.url = duplicate.url or survivor.url
                survivor.seller = duplicate.seller or survivor.seller
                survivor.normalized_seller = (
                    duplicate.normalized_seller or survivor.normalized_seller
                )

    db.flush()
    return archived, moved


def reconcile_lifecycle(
    db,
    *,
    missing_after_hours: int = 36,
    archive_after_hours: int = 96,
) -> tuple[int, int, int]:
    now = datetime.utcnow()
    missing_cutoff = now - timedelta(hours=max(1, missing_after_hours))
    archive_cutoff = now - timedelta(
        hours=max(missing_after_hours + 1, archive_after_hours)
    )

    missing = 0
    archived = 0
    fixed = 0

    for offer in db.query(ProductOffer).all():
        previous = str(offer.lifecycle_status or ACTIVE)
        last_checked = (
            offer.last_checked_at
            or offer.updated_at
            or offer.created_at
            or now
        )
        available = is_offer_available(offer.availability)

        if not offer.is_active:
            target = ARCHIVED
        elif last_checked < archive_cutoff:
            target = ARCHIVED
            offer.is_active = False
            offer.is_best_offer = False
            offer.inactive_at = offer.inactive_at or now
            offer.consecutive_misses = max(int(offer.consecutive_misses or 0), 2)
            archived += 1
        elif last_checked < missing_cutoff:
            target = MISSING
            offer.consecutive_misses = max(int(offer.consecutive_misses or 0), 1)
            missing += 1
        elif not available:
            target = OUT_OF_STOCK
            offer.is_best_offer = False
            offer.consecutive_misses = 0
        else:
            target = UPDATED if previous == UPDATED else ACTIVE
            offer.consecutive_misses = 0
            offer.inactive_at = None

        if previous != target:
            offer.lifecycle_status = target
            fixed += 1

    db.flush()
    return missing, archived, fixed


def recompute_best_offers(db, group_ids: Iterable[int] | None = None) -> int:
    if group_ids is None:
        group_ids = [
            int(value)
            for (value,) in db.query(ProductOffer.group_id).distinct().all()
            if value is not None
        ]

    changed_groups = 0

    for group_id in set(int(value) for value in group_ids):
        rows = (
            db.query(ProductOffer)
            .filter(ProductOffer.group_id == group_id)
            .all()
        )
        old_best = {item.id for item in rows if item.is_best_offer}

        for item in rows:
            item.is_best_offer = False

        eligible = [item for item in rows if _eligible(item)]
        if eligible:
            best = min(eligible, key=lambda item: (_total_price(item), item.id))
            best.is_best_offer = True
            new_best = {best.id}
        else:
            new_best = set()

        if old_best != new_best:
            changed_groups += 1

    db.flush()
    return changed_groups


def offer_health_summary(db) -> dict:
    lifecycle_counts = dict(
        db.query(ProductOffer.lifecycle_status, func.count(ProductOffer.id))
        .group_by(ProductOffer.lifecycle_status)
        .all()
    )

    duplicate_groups = (
        db.query(
            ProductOffer.store_id,
            ProductOffer.dedupe_key,
            func.count(ProductOffer.id),
        )
        .filter(
            ProductOffer.dedupe_key.isnot(None),
            ProductOffer.dedupe_key != "",
        )
        .group_by(ProductOffer.store_id, ProductOffer.dedupe_key)
        .having(func.count(ProductOffer.id) > 1)
        .count()
    )

    now = datetime.utcnow()
    stale_36 = (
        db.query(ProductOffer)
        .filter(
            ProductOffer.is_active.is_(True),
            ProductOffer.last_checked_at < now - timedelta(hours=36),
        )
        .count()
    )
    stale_96 = (
        db.query(ProductOffer)
        .filter(
            ProductOffer.is_active.is_(True),
            ProductOffer.last_checked_at < now - timedelta(hours=96),
        )
        .count()
    )
    missing_dedupe = (
        db.query(ProductOffer)
        .filter(
            (ProductOffer.dedupe_key.is_(None))
            | (ProductOffer.dedupe_key == "")
        )
        .count()
    )

    return {
        "lifecycle": {
            str(key or "UNKNOWN"): int(value)
            for key, value in lifecycle_counts.items()
        },
        "duplicate_groups": int(duplicate_groups or 0),
        "stale_36": int(stale_36 or 0),
        "stale_96": int(stale_96 or 0),
        "missing_dedupe": int(missing_dedupe or 0),
    }


def run_offer_maintenance(db, action: str = "full") -> OfferMaintenanceResult:
    result = OfferMaintenanceResult(
        checked=db.query(ProductOffer).count()
    )
    action = str(action or "full").strip().lower()

    if action in {"full", "dedupe-keys", "duplicates"}:
        result.dedupe_keys_filled = fill_missing_dedupe_keys(db)

    if action in {"full", "duplicates"}:
        (
            result.duplicates_archived,
            result.histories_moved,
        ) = archive_duplicate_offers(db)

    if action in {"full", "lifecycle", "stale"}:
        (
            result.marked_missing,
            result.archived_stale,
            result.status_fixed,
        ) = reconcile_lifecycle(db)

    if action in {"full", "best"}:
        result.best_offer_groups_fixed = recompute_best_offers(db)

    db.flush()
    return result
