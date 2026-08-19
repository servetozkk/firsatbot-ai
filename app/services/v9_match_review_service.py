from __future__ import annotations

from datetime import datetime

from app.database.models import GlobalProduct, ProductDB, ProductOffer, RawProduct
from app.database.v9_models import ProductMatchReview
from app.services.catalog_reconciliation_service import _raw_to_product, sync_global_offer
from app.services.global_catalog_service import sync_raw_and_global_catalog
from app.services.product_identity_service import ProductIdentityService


def approve_match_review(*, db, review_id: int) -> tuple[bool, str]:
    review = db.get(ProductMatchReview, review_id)
    if review is None or review.status != "PENDING":
        return False, "Bekleyen inceleme kaydı bulunamadı."
    raw = db.get(RawProduct, review.raw_product_id)
    candidate = db.get(GlobalProduct, review.candidate_global_product_id) if review.candidate_global_product_id else None
    if raw is None or candidate is None:
        return False, "Ham ürün veya aday global ürün bulunamadı."

    product = ProductIdentityService.enrich_product(_raw_to_product(raw))
    identity = ProductIdentityService.explain(product)
    identity["identity_key"] = candidate.identity_key
    identity["identity_source"] = candidate.identity_source or identity.get("identity_source")

    legacy_product = db.get(ProductDB, raw.legacy_product_id) if raw.legacy_product_id else None
    raw, global_product, _variant = sync_raw_and_global_catalog(
        db=db,
        product=product,
        legacy_product_id=legacy_product.id if legacy_product is not None else None,
        identity_info=identity,
    )
    legacy_offer = (
        db.query(ProductOffer).filter(ProductOffer.product_id == legacy_product.id).first()
        if legacy_product is not None else None
    )
    offer = sync_global_offer(db=db, raw=raw, legacy_offer=legacy_offer)
    if offer is None:
        return False, "Global teklif oluşturulamadı."

    raw.reconciliation_status = "MATCHED"
    raw.reconciliation_score = review.confidence
    raw.reconciliation_error = None
    raw.reconciled_at = datetime.utcnow()
    review.status = "APPROVED"
    review.resolved_at = datetime.utcnow()
    review.updated_at = datetime.utcnow()
    review.decision_note = "Aday global ürüne manuel bağlandı."
    db.commit()
    return True, f"Global ürün {global_product.id} ile eşleştirildi."


def reject_match_review(*, db, review_id: int) -> tuple[bool, str]:
    review = db.get(ProductMatchReview, review_id)
    if review is None or review.status != "PENDING":
        return False, "Bekleyen inceleme kaydı bulunamadı."
    raw = db.get(RawProduct, review.raw_product_id)
    if raw is None:
        return False, "Ham ürün bulunamadı."

    product = ProductIdentityService.enrich_product(_raw_to_product(raw))
    identity = ProductIdentityService.explain(product)
    legacy_product = db.get(ProductDB, raw.legacy_product_id) if raw.legacy_product_id else None
    raw, global_product, _variant = sync_raw_and_global_catalog(
        db=db,
        product=product,
        legacy_product_id=legacy_product.id if legacy_product is not None else None,
        identity_info=identity,
    )
    legacy_offer = (
        db.query(ProductOffer).filter(ProductOffer.product_id == legacy_product.id).first()
        if legacy_product is not None else None
    )
    offer = sync_global_offer(db=db, raw=raw, legacy_offer=legacy_offer)
    if offer is None:
        return False, "Yeni global teklif oluşturulamadı."

    raw.reconciliation_status = "MATCHED"
    raw.reconciliation_error = None
    raw.reconciled_at = datetime.utcnow()
    review.status = "REJECTED_NEW_PRODUCT"
    review.resolved_at = datetime.utcnow()
    review.updated_at = datetime.utcnow()
    review.decision_note = "Aday reddedildi; ayrı global ürün oluşturuldu."
    db.commit()
    return True, f"Yeni global ürün {global_product.id} oluşturuldu."
