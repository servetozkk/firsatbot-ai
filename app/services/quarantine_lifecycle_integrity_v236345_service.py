from __future__ import annotations

from datetime import datetime

from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, ProductOffer
from app.services.performance_cache_service import invalidate_global_catalog_cache

QUARANTINED = "QUARANTINED"
ACTIVE = "ACTIVE"


def run_quarantine_lifecycle_integrity_v236345() -> dict:
    """Converge every quarantined offer to one fail-closed lifecycle state.

    This does not decide whether an offer should be quarantined. Existing price-
    integrity and source-identity decisions are preserved. It only normalizes
    lifecycle flags and recomputes GlobalProduct.active_offer_count from serving-
    eligible GlobalOffer rows.
    """
    db = SessionLocal()
    offer_fixed = legacy_fixed = counter_fixed = 0
    affected: set[int] = set()
    try:
        quarantined = (
            db.query(GlobalOffer)
            .filter(GlobalOffer.lifecycle_status == QUARANTINED)
            .all()
        )
        for offer in quarantined:
            changed = False
            if bool(offer.is_active):
                offer.is_active = False
                changed = True
            if not bool(offer.is_hidden):
                offer.is_hidden = True
                changed = True
            if changed:
                offer.updated_at = datetime.utcnow()
                offer_fixed += 1
                affected.add(int(offer.global_product_id))

            if offer.legacy_offer_id:
                legacy = db.get(ProductOffer, int(offer.legacy_offer_id))
                if legacy is not None:
                    legacy_changed = False
                    if bool(legacy.is_active):
                        legacy.is_active = False
                        legacy_changed = True
                    if not bool(legacy.is_hidden):
                        legacy.is_hidden = True
                        legacy_changed = True
                    if str(legacy.lifecycle_status or "").upper() != QUARANTINED:
                        legacy.lifecycle_status = QUARANTINED
                        legacy_changed = True
                    if legacy_changed:
                        legacy.updated_at = datetime.utcnow()
                        legacy_fixed += 1

        offer_counts = dict(
            db.query(GlobalOffer.global_product_id, func.count(GlobalOffer.id))
            .filter(
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
                GlobalOffer.lifecycle_status == ACTIVE,
                GlobalOffer.current_price > 0,
            )
            .group_by(GlobalOffer.global_product_id)
            .all()
        )
        for gp in db.query(GlobalProduct).all():
            expected = int(offer_counts.get(gp.id, 0))
            if int(gp.active_offer_count or 0) != expected:
                gp.active_offer_count = expected
                gp.updated_at = datetime.utcnow()
                counter_fixed += 1
                affected.add(int(gp.id))

        db.commit()
        invalidate_global_catalog_cache()
        return {
            "runtime_version": "23.63.45",
            "quarantined_offer_count": len(quarantined),
            "offer_state_fixed_count": offer_fixed,
            "legacy_state_fixed_count": legacy_fixed,
            "active_offer_counter_fixed_count": counter_fixed,
            "affected_global_product_count": len(affected),
            "policy": "quarantined-implies-inactive-and-hidden",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
