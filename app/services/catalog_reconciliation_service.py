from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.database.models import (
    GlobalOffer,
    GlobalProduct,
    GlobalProductVariant,
    ProductDB,
    ProductOffer,
    RawProduct,
)
from app.models.product import Product
from app.services.global_catalog_service import sync_raw_and_global_catalog
from app.services.product_identity_service import ProductIdentityService
from app.services.operational_log_service import record_operation_event
from app.services.performance_cache_service import invalidate_global_catalog_cache
from app.services.global_price_history_service import record_global_offer_price
from app.services.price_integrity_v219_service import evaluate_price_candidate, quarantine_offer, quarantine_legacy_offer
from app.database.v9_models import ProductMatchReview
from app.services.v9_identity_matching_service import decide_global_match
from app.services.source_identity_integrity_v236344_service import apply_source_identity_guard_v236344


def _json_value(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def _raw_to_product(raw: RawProduct) -> Product:
    return Product(
        name=raw.title_raw,
        price=float(raw.price_raw or 0),
        old_price=raw.old_price_raw,
        rating=None,
        review_count=None,
        seller=raw.seller_raw or raw.store_code,
        url=raw.source_url,
        image=raw.image_raw,
        image_gallery=_json_value(raw.gallery_raw),
        brand=raw.brand_raw,
        model=raw.model_raw,
        category=raw.category_raw,
        description=raw.description_raw,
        specifications=_json_value(raw.specifications_raw),
        stock_status=raw.stock_raw or "Bilinmiyor",
        source_site=raw.store_code,
        product_code=raw.store_product_id,
    )


def _offer_total(offer: GlobalOffer) -> float:
    return float(offer.current_price or 0) + float(offer.shipping_price or 0)


def sync_global_offer(
    *,
    db,
    raw: RawProduct,
    legacy_offer: ProductOffer | None,
) -> GlobalOffer | None:
    if raw.global_product_id is None:
        return None

    now = datetime.utcnow()
    current_price = (
        float(legacy_offer.current_price)
        if legacy_offer is not None
        else float(raw.price_raw or 0)
    )
    if current_price <= 0:
        raw.reconciliation_status = "INVALID"
        raw.reconciliation_error = "Geçerli fiyat bulunamadı."
        raw.updated_at = now
        return None

    offer = (
        db.query(GlobalOffer)
        .filter(GlobalOffer.raw_product_id == raw.id)
        .first()
    )

    price_verdict = evaluate_price_candidate(
        db=db,
        global_product_id=int(raw.global_product_id),
        store_code=str(raw.store_code or "").casefold(),
        candidate_price=current_price,
        existing_offer=offer,
    )

    # Yeni scrape aşırı anomaliyse daha önce doğrulanmış aktif GlobalOffer'ı
    # bozmayız. Yanlış yeni fiyat legacy/raw katmanda teşhis için kalabilir,
    # fakat kullanıcıya sunulan son güvenilir teklif korunur.
    if (
        not price_verdict.trusted
        and offer is not None
        and bool(offer.is_active)
        and not bool(offer.is_hidden)
        and str(offer.lifecycle_status or "ACTIVE").upper() == "ACTIVE"
        and float(offer.current_price or 0) > 0
        and abs(float(offer.current_price) - current_price) > 0.01
    ):
        quarantine_legacy_offer(legacy_offer, price_verdict.reason)
        raw.reconciliation_status = "PRICE_QUARANTINED"
        raw.reconciliation_error = price_verdict.reason
        raw.updated_at = now
        print(
            f"V21.9 fiyat karantinası [{raw.store_code}]: "
            f"aday={current_price:.2f}, mevcut güvenilir={float(offer.current_price):.2f}; "
            "GlobalOffer korunuyor."
        )
        return offer

    if offer is None:
        offer = GlobalOffer(
            global_product_id=raw.global_product_id,
            global_variant_id=raw.global_variant_id,
            raw_product_id=raw.id,
            legacy_offer_id=(legacy_offer.id if legacy_offer else None),
            store_code=raw.store_code,
            store_product_id=raw.store_product_id,
            seller=(
                legacy_offer.seller
                if legacy_offer is not None
                else raw.seller_raw
            ),
            url=(
                legacy_offer.url
                if legacy_offer is not None
                else raw.source_url
            ),
            current_price=current_price,
            old_price=(
                legacy_offer.old_price
                if legacy_offer is not None
                else raw.old_price_raw
            ),
            shipping_price=(
                legacy_offer.shipping_price
                if legacy_offer is not None
                else None
            ),
            currency=(
                legacy_offer.currency
                if legacy_offer is not None
                else "TRY"
            ),
            availability=(
                legacy_offer.availability
                if legacy_offer is not None
                else (raw.stock_raw or "Bilinmiyor")
            ),
            delivery_text=(
                legacy_offer.delivery_text
                if legacy_offer is not None
                else None
            ),
            warranty_type=(
                legacy_offer.warranty_type
                if legacy_offer is not None
                else None
            ),
            campaign_text=(
                legacy_offer.campaign_text
                if legacy_offer is not None
                else None
            ),
            installment_text=(
                legacy_offer.installment_text
                if legacy_offer is not None
                else None
            ),
            is_official_seller=bool(
                legacy_offer.is_official_seller
                if legacy_offer is not None
                else False
            ),
            is_active=bool(
                legacy_offer.is_active
                if legacy_offer is not None
                else True
            ),
            is_hidden=bool(
                legacy_offer.is_hidden
                if legacy_offer is not None
                else False
            ),
            lifecycle_status=(
                legacy_offer.lifecycle_status
                if legacy_offer is not None
                else "ACTIVE"
            ),
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(offer)
        db.flush()
    else:
        offer.global_product_id = raw.global_product_id
        offer.global_variant_id = raw.global_variant_id
        offer.legacy_offer_id = (
            legacy_offer.id if legacy_offer else offer.legacy_offer_id
        )
        offer.store_code = raw.store_code
        offer.store_product_id = raw.store_product_id
        offer.seller = (
            legacy_offer.seller
            if legacy_offer is not None
            else (raw.seller_raw or offer.seller)
        )
        offer.url = (
            legacy_offer.url
            if legacy_offer is not None
            else raw.source_url
        )
        offer.current_price = current_price
        offer.old_price = (
            legacy_offer.old_price
            if legacy_offer is not None
            else raw.old_price_raw
        )
        if legacy_offer is not None:
            offer.shipping_price = legacy_offer.shipping_price
            offer.currency = legacy_offer.currency or "TRY"
            offer.availability = legacy_offer.availability
            offer.delivery_text = legacy_offer.delivery_text
            offer.warranty_type = legacy_offer.warranty_type
            offer.campaign_text = legacy_offer.campaign_text
            offer.installment_text = legacy_offer.installment_text
            offer.is_official_seller = bool(
                legacy_offer.is_official_seller
            )
            offer.is_active = bool(legacy_offer.is_active)
            offer.is_hidden = bool(legacy_offer.is_hidden)
            offer.lifecycle_status = (
                legacy_offer.lifecycle_status or "ACTIVE"
            )
        offer.last_seen_at = now
        offer.updated_at = now

    if not price_verdict.trusted:
        quarantine_legacy_offer(legacy_offer, price_verdict.reason)
        quarantine_offer(db=db, offer=offer, verdict=price_verdict)
        raw.reconciliation_status = "PRICE_QUARANTINED"
        raw.reconciliation_error = price_verdict.reason
        print(
            f"V21.9 fiyat karantinası [{raw.store_code}]: "
            f"{current_price:.2f} TL -> QUARANTINED | {price_verdict.reason}"
        )
        db.flush()
        return offer

    # V23.63.44: independent raw/source evidence must not strongly contradict
    # the canonical product. A single weak parser conflict is insufficient;
    # strong semantic URL or canonical-override hardware/series contradictions
    # fail closed before price history/serving activation.
    source_identity_verdict = apply_source_identity_guard_v236344(
        db=db,
        raw=raw,
        offer=offer,
    )
    if source_identity_verdict.quarantine:
        _refresh_global_product_offer_count(
            db=db,
            global_product_id=raw.global_product_id,
        )
        db.flush()
        return offer

    record_global_offer_price(
        db=db,
        offer=offer,
        checked_at=now,
    )
    _deduplicate_store_offers(
        db=db,
        global_product_id=raw.global_product_id,
        store_code=raw.store_code,
    )
    _refresh_global_product_offer_count(
        db=db,
        global_product_id=raw.global_product_id,
    )
    return offer


def _deduplicate_store_offers(
    *,
    db,
    global_product_id: int,
    store_code: str,
) -> None:
    offers = (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.global_product_id == global_product_id,
            GlobalOffer.store_code == store_code,
            GlobalOffer.lifecycle_status.notin_(("MISSING", "QUARANTINED")),
        )
        .all()
    )
    valid = [
        item
        for item in offers
        if float(item.current_price or 0) > 0
    ]
    if not valid:
        return

    winner = min(
        valid,
        key=lambda item: (
            _offer_total(item),
            -(item.last_seen_at or item.updated_at or item.created_at).timestamp(),
            item.id,
        ),
    )
    for item in valid:
        if item.id == winner.id:
            item.is_active = True
            item.is_hidden = False
            item.lifecycle_status = "ACTIVE"
            item.duplicate_reason = None
        else:
            item.is_active = False
            item.is_hidden = True
            item.lifecycle_status = "ARCHIVED"
            item.duplicate_reason = (
                "Aynı global ürün ve mağaza için daha avantajlı "
                "bir teklif aktif bırakıldı."
            )


def _refresh_global_product_offer_count(
    *,
    db,
    global_product_id: int,
) -> None:
    count = (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.global_product_id == global_product_id,
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == "ACTIVE",
        )
        .count()
    )
    global_product = db.get(GlobalProduct, global_product_id)
    if global_product is not None:
        global_product.active_offer_count = count
        global_product.updated_at = datetime.utcnow()



def _create_or_update_review(*, db, raw: RawProduct, identity: dict[str, Any], decision):
    review = (
        db.query(ProductMatchReview)
        .filter(
            ProductMatchReview.raw_product_id == raw.id,
            ProductMatchReview.status == "PENDING",
        )
        .first()
    )
    if review is None:
        review = ProductMatchReview(
            raw_product_id=raw.id,
            status="PENDING",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(review)

    review.candidate_global_product_id = decision.candidate_global_product_id
    review.proposed_identity_key = identity.get("identity_key")
    review.confidence = float(decision.confidence)
    review.reasons_json = json.dumps(decision.reasons, ensure_ascii=False)
    review.conflicts_json = json.dumps(decision.conflicts, ensure_ascii=False)
    review.identifiers_json = json.dumps(decision.identifiers, ensure_ascii=False, default=str)
    review.updated_at = datetime.utcnow()

    raw.reconciliation_status = "REVIEW_REQUIRED"
    raw.reconciliation_score = float(decision.confidence)
    raw.reconciliation_error = "; ".join(decision.conflicts) or "Manuel eşleşme incelemesi gerekiyor."
    raw.reconciled_at = datetime.utcnow()
    raw.updated_at = datetime.utcnow()
    db.flush()
    return review


def _apply_candidate_identity(identity: dict[str, Any], candidate: GlobalProduct) -> dict[str, Any]:
    updated = dict(identity)
    updated["identity_key"] = candidate.identity_key
    updated["identity_source"] = candidate.identity_source or identity.get("identity_source")
    return updated


def reconcile_raw_product(
    *,
    db,
    raw: RawProduct,
) -> tuple[bool, str]:
    now = datetime.utcnow()
    raw.reconciliation_status = "PROCESSING"
    raw.reconciliation_error = None
    raw.updated_at = now
    db.flush()

    try:
        legacy_product = (
            db.get(ProductDB, raw.legacy_product_id)
            if raw.legacy_product_id
            else None
        )
        product = _raw_to_product(raw)
        product = ProductIdentityService.enrich_product(product)
        identity = ProductIdentityService.explain(product)
        decision = decide_global_match(
            db=db,
            raw=raw,
            identity=identity,
        )

        if decision.action == "REVIEW":
            review = _create_or_update_review(
                db=db,
                raw=raw,
                identity=identity,
                decision=decision,
            )
            return False, (
                f"İnceleme gerekli: review={review.id}, "
                f"güven={decision.confidence:.1f}"
            )

        if (
            decision.action == "AUTO_MATCH"
            and decision.candidate_global_product_id is not None
        ):
            candidate = db.get(
                GlobalProduct,
                decision.candidate_global_product_id,
            )
            if candidate is not None:
                identity = _apply_candidate_identity(identity, candidate)

        raw, global_product, variant = sync_raw_and_global_catalog(
            db=db,
            product=product,
            legacy_product_id=(
                legacy_product.id if legacy_product is not None else None
            ),
            identity_info=identity,
        )
        raw.reconciliation_score = float(decision.confidence)

        legacy_offer = None
        if legacy_product is not None:
            legacy_offer = (
                db.query(ProductOffer)
                .filter(ProductOffer.product_id == legacy_product.id)
                .first()
            )

        global_offer = sync_global_offer(
            db=db,
            raw=raw,
            legacy_offer=legacy_offer,
        )
        if global_offer is None:
            raise ValueError("Global teklif oluşturulamadı.")

        # V23.63.44 source/canonical contradiction quarantine is authoritative.
        # Do not overwrite the raw telemetry back to MATCHED after the offer
        # has been fail-closed by sync_global_offer().
        if str(raw.reconciliation_status or "").upper() == "QUARANTINED":
            raw.reconciled_at = now
            raw.updated_at = now
            db.flush()
            return True, (
                f"Global ürün {global_product.id}, varyant {variant.id}, "
                f"teklif {global_offer.id} SOURCE_IDENTITY_QUARANTINED"
            )

        raw.reconciliation_status = "MATCHED"
        raw.reconciliation_score = 100.0
        raw.reconciliation_error = None
        raw.reconciled_at = now
        raw.updated_at = now
        db.flush()
        return True, (
            f"Global ürün {global_product.id}, varyant {variant.id}, "
            f"teklif {global_offer.id}"
        )
    except Exception as error:
        record_operation_event(level="ERROR", source="reconciliation", event_type="raw_product_failed", message=f"{type(error).__name__}: {error}", details={"raw_product_id": raw.id, "store_code": raw.store_code, "source_url": raw.source_url})
        raw.reconciliation_status = "FAILED"
        raw.reconciliation_error = (
            f"{type(error).__name__}: {error}"
        )
        raw.reconciled_at = now
        raw.updated_at = now
        db.flush()
        return False, raw.reconciliation_error


def process_reconciliation_queue(
    *,
    db,
    limit: int = 500,
    retry_failed: bool = False,
) -> dict[str, Any]:
    statuses = ["PENDING", "PROCESSING"]
    if retry_failed:
        statuses.append("FAILED")

    rows = (
        db.query(RawProduct)
        .filter(RawProduct.reconciliation_status.in_(statuses))
        .order_by(RawProduct.id.asc())
        .limit(max(1, min(int(limit), 5000)))
        .all()
    )

    processed = matched = failed = 0
    messages: list[str] = []

    for raw in rows:
        processed += 1
        success, message = reconcile_raw_product(db=db, raw=raw)
        if success:
            matched += 1
        else:
            failed += 1
        messages.append(f"raw={raw.id}: {message}")

    db.commit()
    return {
        "processed": processed,
        "matched": matched,
        "failed": failed,
        "messages": messages[-100:],
    }


def reconciliation_summary(db) -> dict[str, int]:
    statuses = {
        key: (
            db.query(RawProduct)
            .filter(RawProduct.reconciliation_status == key)
            .count()
        )
        for key in (
            "PENDING",
            "PROCESSING",
            "MATCHED",
            "FAILED",
            "INVALID",
            "REVIEW_REQUIRED",
        )
    }
    statuses.update(
        {
            "raw_products": db.query(RawProduct).count(),
            "global_products": db.query(GlobalProduct).count(),
            "global_variants": db.query(GlobalProductVariant).count(),
            "global_offers": db.query(GlobalOffer).count(),
            "match_reviews": (
                db.query(ProductMatchReview)
                .filter(ProductMatchReview.status == "PENDING")
                .count()
            ),
            "active_global_offers": (
                db.query(GlobalOffer)
                .filter(
                    GlobalOffer.is_active.is_(True),
                    GlobalOffer.is_hidden.is_(False),
                    GlobalOffer.lifecycle_status == "ACTIVE",
                )
                .count()
            ),
        }
    )
    return statuses
