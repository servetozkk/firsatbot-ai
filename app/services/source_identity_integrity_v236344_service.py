from __future__ import annotations

from datetime import datetime

from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, ProductOffer, RawProduct
from app.services.performance_cache_service import invalidate_global_catalog_cache
from app.services.source_identity_policy_v236344 import (
    SourceIdentityVerdict,
    evaluate_source_identity_values_v236344,
)

QUARANTINED = "QUARANTINED"
_REASON_PREFIX = "SOURCE_IDENTITY_V236344"


def evaluate_source_identity_v236344(raw: RawProduct, global_product: GlobalProduct) -> SourceIdentityVerdict:
    return evaluate_source_identity_values_v236344(
        store_code=str(raw.store_code or ""),
        source_url=str(raw.source_url or ""),
        raw_title=str(raw.title_raw or ""),
        identity_payload=raw.identity_payload,
        canonical_name=str(global_product.canonical_name or ""),
    )

def quarantine_source_identity_v236344(*, db, raw: RawProduct, offer: GlobalOffer, verdict: SourceIdentityVerdict) -> None:
    if not verdict.quarantine:
        return
    now = datetime.utcnow()
    reason = f"{_REASON_PREFIX} | {verdict.reason_text}"

    raw.reconciliation_status = QUARANTINED
    raw.reconciliation_error = reason
    raw.reconciled_at = now
    raw.updated_at = now

    offer.is_active = False
    offer.is_hidden = True
    offer.lifecycle_status = QUARANTINED
    offer.duplicate_reason = reason
    offer.updated_at = now

    if offer.legacy_offer_id:
        legacy = db.get(ProductOffer, int(offer.legacy_offer_id))
        if legacy is not None:
            legacy.is_active = False
            legacy.is_hidden = True
            legacy.lifecycle_status = QUARANTINED
            legacy.updated_at = now


def apply_source_identity_guard_v236344(*, db, raw: RawProduct, offer: GlobalOffer) -> SourceIdentityVerdict:
    global_product = db.get(GlobalProduct, int(raw.global_product_id)) if raw.global_product_id else None
    if global_product is None:
        return SourceIdentityVerdict(False, ())
    verdict = evaluate_source_identity_v236344(raw, global_product)
    if verdict.quarantine:
        quarantine_source_identity_v236344(db=db, raw=raw, offer=offer, verdict=verdict)
    return verdict


def _refresh_counts(db) -> int:
    raw_counts = dict(
        db.query(RawProduct.global_product_id, func.count(RawProduct.id))
        .filter(RawProduct.global_product_id.is_not(None))
        .group_by(RawProduct.global_product_id).all()
    )
    offer_counts = dict(
        db.query(GlobalOffer.global_product_id, func.count(GlobalOffer.id))
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == "ACTIVE",
            GlobalOffer.current_price > 0,
        )
        .group_by(GlobalOffer.global_product_id).all()
    )
    fixed = 0
    for gp in db.query(GlobalProduct).all():
        expected_raw = int(raw_counts.get(gp.id, 0))
        expected_offer = int(offer_counts.get(gp.id, 0))
        if int(gp.raw_product_count or 0) != expected_raw or int(gp.active_offer_count or 0) != expected_offer:
            gp.raw_product_count = expected_raw
            gp.active_offer_count = expected_offer
            gp.updated_at = datetime.utcnow()
            fixed += 1
    return fixed


def run_source_identity_integrity_v236344() -> dict:
    db = SessionLocal()
    checked = quarantined_raw = quarantined_offer = already_quarantined = 0
    affected: set[int] = set()
    try:
        rows = (
            db.query(RawProduct, GlobalOffer, GlobalProduct)
            .join(GlobalOffer, GlobalOffer.raw_product_id == RawProduct.id)
            .join(GlobalProduct, GlobalProduct.id == RawProduct.global_product_id)
            .all()
        )
        for raw, offer, global_product in rows:
            checked += 1
            verdict = evaluate_source_identity_v236344(raw, global_product)
            if not verdict.quarantine:
                continue
            reason = str(offer.duplicate_reason or "")
            if str(offer.lifecycle_status or "").upper() == QUARANTINED and reason.startswith(_REASON_PREFIX):
                already_quarantined += 1
                continue
            quarantine_source_identity_v236344(db=db, raw=raw, offer=offer, verdict=verdict)
            quarantined_raw += 1
            quarantined_offer += 1
            affected.add(int(global_product.id))

        counter_fixed = _refresh_counts(db)
        db.commit()
        invalidate_global_catalog_cache()
        return {
            "runtime_version": "23.63.44",
            "checked_link_count": checked,
            "quarantined_raw_count": quarantined_raw,
            "quarantined_offer_count": quarantined_offer,
            "already_quarantined_count": already_quarantined,
            "counter_reconciled_product_count": counter_fixed,
            "affected_global_product_count": len(affected),
            "opaque_url_policy": "amazon-asin-url-not-semantic-evidence",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
