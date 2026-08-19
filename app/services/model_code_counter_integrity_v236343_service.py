from __future__ import annotations

from datetime import datetime

from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, GlobalProductVariant, RawProduct
from app.services.performance_cache_service import invalidate_global_catalog_cache
from app.services.product_identity_service import ProductIdentityService


def run_model_code_counter_integrity_v236343() -> dict:
    """Repair proven pseudo model-code residue and denormalized counters.

    Variant keys are deliberately not rewritten in this release.  V23.63.41
    established referential variant stability, so V23.63.43 only removes the
    invalid model_code payload while keeping IDs/variant_key references stable.
    Counters are derived from authoritative child tables, never staging links.
    """
    db = SessionLocal()
    gp_model_fixed = variant_model_fixed = raw_counter_fixed = offer_counter_fixed = 0
    affected: set[int] = set()
    try:
        for gp in db.query(GlobalProduct).filter(GlobalProduct.model_code.is_not(None)).all():
            if ProductIdentityService._is_pseudo_model_code(gp.model_code):
                gp.model_code = None
                gp.updated_at = datetime.utcnow()
                gp_model_fixed += 1
                affected.add(int(gp.id))

        for variant in db.query(GlobalProductVariant).filter(GlobalProductVariant.model_code.is_not(None)).all():
            if ProductIdentityService._is_pseudo_model_code(variant.model_code):
                variant.model_code = None
                variant.updated_at = datetime.utcnow()
                variant_model_fixed += 1
                affected.add(int(variant.global_product_id))

        raw_counts = dict(
            db.query(RawProduct.global_product_id, func.count(RawProduct.id))
            .filter(RawProduct.global_product_id.is_not(None))
            .group_by(RawProduct.global_product_id)
            .all()
        )
        offer_counts = dict(
            db.query(GlobalOffer.global_product_id, func.count(GlobalOffer.id))
            .filter(
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
                GlobalOffer.lifecycle_status == "ACTIVE",
                GlobalOffer.current_price > 0,
            )
            .group_by(GlobalOffer.global_product_id)
            .all()
        )

        for gp in db.query(GlobalProduct).all():
            raw_count = int(raw_counts.get(gp.id, 0))
            offer_count = int(offer_counts.get(gp.id, 0))
            changed = False
            if int(gp.raw_product_count or 0) != raw_count:
                gp.raw_product_count = raw_count
                raw_counter_fixed += 1
                changed = True
            if int(gp.active_offer_count or 0) != offer_count:
                gp.active_offer_count = offer_count
                offer_counter_fixed += 1
                changed = True
            if changed:
                gp.updated_at = datetime.utcnow()
                affected.add(int(gp.id))

        db.commit()
        invalidate_global_catalog_cache()
        return {
            "runtime_version": "23.63.43",
            "global_product_model_code_fixed": gp_model_fixed,
            "variant_model_code_fixed": variant_model_fixed,
            "raw_product_counter_fixed": raw_counter_fixed,
            "active_offer_counter_fixed": offer_counter_fixed,
            "affected_global_product_count": len(affected),
            "variant_key_rewrite_count": 0,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
