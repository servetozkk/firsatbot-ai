from __future__ import annotations

from datetime import datetime

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalOfferPriceHistory, GlobalProductVariant, RawProduct


def _norm(value):
    text = " ".join(str(value or "").split()).strip().casefold()
    return text or None


def run_variant_referential_convergence_v236341() -> dict:
    """Fail-closed repair of GlobalOffer -> RawProduct variant drift.

    Only active offers with a MATCHED raw product are considered. The target raw
    variant must belong to the same GlobalProduct, model codes may not conflict,
    and no already-authoritative color/network dimension may be lost or changed.
    """
    db = SessionLocal()
    checked = repaired = history_relinked = unsafe = 0
    affected_products: set[int] = set()
    try:
        rows = (
            db.query(GlobalOffer, RawProduct)
            .join(RawProduct, RawProduct.id == GlobalOffer.raw_product_id)
            .filter(
                GlobalOffer.is_active.is_(True),
                GlobalOffer.global_variant_id.is_not(None),
                RawProduct.global_variant_id.is_not(None),
                GlobalOffer.global_variant_id != RawProduct.global_variant_id,
                RawProduct.reconciliation_status == "MATCHED",
            )
            .all()
        )
        for offer, raw in rows:
            checked += 1
            old = db.get(GlobalProductVariant, int(offer.global_variant_id))
            new = db.get(GlobalProductVariant, int(raw.global_variant_id))
            reasons = []
            if old is None or new is None:
                reasons.append("MISSING_VARIANT")
            else:
                gp = int(offer.global_product_id)
                if int(raw.global_product_id or 0) != gp:
                    reasons.append("RAW_GLOBAL_PRODUCT_MISMATCH")
                if int(old.global_product_id or 0) != gp:
                    reasons.append("OLD_VARIANT_GLOBAL_PRODUCT_MISMATCH")
                if int(new.global_product_id or 0) != gp:
                    reasons.append("NEW_VARIANT_GLOBAL_PRODUCT_MISMATCH")
                old_model, new_model = _norm(old.model_code), _norm(new.model_code)
                if old_model and new_model and old_model != new_model:
                    reasons.append("MODEL_CONFLICT")
                old_color, new_color = _norm(old.color), _norm(new.color)
                if old_color and old_color != new_color:
                    reasons.append("COLOR_CONFLICT_OR_LOSS")
                old_network, new_network = _norm(old.network), _norm(new.network)
                if old_network and old_network != new_network:
                    reasons.append("NETWORK_CONFLICT_OR_LOSS")
            if reasons:
                unsafe += 1
                continue

            target_id = int(raw.global_variant_id)
            offer.global_variant_id = target_id
            offer.updated_at = datetime.utcnow()
            affected_products.add(int(offer.global_product_id))
            repaired += 1

            histories = (
                db.query(GlobalOfferPriceHistory)
                .filter(GlobalOfferPriceHistory.global_offer_id == offer.id)
                .all()
            )
            for history in histories:
                if history.global_variant_id != target_id:
                    history.global_variant_id = target_id
                    history_relinked += 1

        db.commit()
        return {
            "runtime_version": "23.63.41",
            "checked_drift_count": checked,
            "repaired_offer_count": repaired,
            "history_relinked_count": history_relinked,
            "unsafe_count": unsafe,
            "affected_global_product_count": len(affected_products),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
