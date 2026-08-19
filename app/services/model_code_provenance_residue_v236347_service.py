from __future__ import annotations

from datetime import datetime

from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import GlobalProduct, GlobalProductVariant
from app.services.performance_cache_service import invalidate_global_catalog_cache
from app.services.product_identity_service import ProductIdentityService


def run_canonical_evidence_integrity_v236347() -> dict:
    """Clean proven pseudo model-code residue without merging canonical products.

    V23.63.47 preserves the V23.63.46 fail-closed duplicate policy and fail-closed on duplicate convergence.  The raw
    evidence audit showed real SKU/network/storage distinctions inside several
    brand+family groups, so this release hardens provenance but performs zero
    automatic GlobalProduct merges and zero variant-key rewrites.
    """
    db = SessionLocal()
    gp_fixed = variant_fixed = 0
    affected: set[int] = set()
    try:
        for gp in db.query(GlobalProduct).filter(GlobalProduct.model_code.is_not(None)).all():
            if ProductIdentityService._is_pseudo_model_code(gp.model_code):
                gp.model_code = None
                gp.updated_at = datetime.utcnow()
                gp_fixed += 1
                affected.add(int(gp.id))

        for variant in db.query(GlobalProductVariant).filter(GlobalProductVariant.model_code.is_not(None)).all():
            if ProductIdentityService._is_pseudo_model_code(variant.model_code):
                variant.model_code = None
                variant.updated_at = datetime.utcnow()
                variant_fixed += 1
                affected.add(int(variant.global_product_id))

        duplicate_group_count = int(
            db.query(func.count())
            .select_from(
                db.query(GlobalProduct.normalized_brand, GlobalProduct.family)
                .filter(
                    GlobalProduct.status == "ACTIVE",
                    GlobalProduct.normalized_brand.is_not(None),
                    GlobalProduct.family.is_not(None),
                )
                .group_by(GlobalProduct.normalized_brand, GlobalProduct.family)
                .having(func.count(GlobalProduct.id) > 1)
                .subquery()
            )
            .scalar()
            or 0
        )

        db.commit()
        if gp_fixed or variant_fixed:
            invalidate_global_catalog_cache()
        return {
            "runtime_version": "23.63.47",
            "global_product_model_code_fixed": gp_fixed,
            "variant_model_code_fixed": variant_fixed,
            "affected_global_product_count": len(affected),
            "duplicate_candidate_group_count": duplicate_group_count,
            "automatic_merge_count": 0,
            "variant_key_rewrite_count": 0,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
