from __future__ import annotations

from typing import Any

from app.database.models import ProductGroup, ProductOffer, Store
from app.services.offer_ranking_service import enrich_offer_rankings
from app.services.multi_store_service import (
    calculate_offer_total_price,
    is_offer_available,
)


_VISIBLE_LIFECYCLE = {"ACTIVE", "UPDATED", "OUT_OF_STOCK"}


def _value(row: Any, field: str, default: Any = None) -> Any:
    """Eski şemalarla geriye dönük uyumlu alan okuyucu."""
    return getattr(row, field, default)


def get_product_comparison(
    db,
    identity_key: str,
) -> dict[str, Any] | None:
    """Ürün grubunun profesyonel teklif ve mağaza karşılaştırma özetini üretir."""
    group = (
        db.query(ProductGroup)
        .filter(ProductGroup.group_key == identity_key)
        .first()
    )

    if group is None:
        return None

    query = (
        db.query(ProductOffer, Store)
        .join(Store, ProductOffer.store_id == Store.id)
        .filter(ProductOffer.group_id == group.id)
    )

    # Aşama 1/2 kuruluysa arşivlenmiş teklifleri kullanıcı ekranından çıkar.
    if hasattr(ProductOffer, "lifecycle_status"):
        query = query.filter(
            ProductOffer.lifecycle_status.in_(tuple(_VISIBLE_LIFECYCLE))
        )
    if hasattr(ProductOffer, "is_active"):
        query = query.filter(
            (ProductOffer.is_active.is_(True))
            | (ProductOffer.lifecycle_status == "OUT_OF_STOCK")
        )

    rows = query.all()
    offers: list[dict[str, Any]] = []

    for offer, store in rows:
        current_price = float(offer.current_price or 0)
        shipping_price = float(offer.shipping_price or 0)
        total_price = float(calculate_offer_total_price(offer))
        lifecycle = str(_value(offer, "lifecycle_status", "ACTIVE") or "ACTIVE")
        active = bool(_value(offer, "is_active", True))
        available = (
            active
            and lifecycle in {"ACTIVE", "UPDATED"}
            and current_price > 0
            and is_offer_available(offer.availability)
        )

        old_price = float(offer.old_price or 0)
        discount_amount = max(old_price - current_price, 0.0) if old_price else 0.0
        discount_percent = (
            round(discount_amount / old_price * 100, 2)
            if old_price > 0 and discount_amount > 0
            else 0.0
        )

        offers.append(
            {
                "offer_id": offer.id,
                "store": store.name,
                "store_code": store.code,
                "seller": offer.seller,
                "normalized_seller": _value(offer, "normalized_seller"),
                "price": current_price,
                "shipping_price": shipping_price,
                "total_price": round(total_price, 2),
                "old_price": old_price,
                "discount_amount": round(discount_amount, 2),
                "discount_percent": discount_percent,
                "currency": _value(offer, "currency", "TRY") or "TRY",
                "availability": offer.availability,
                "rating": float(offer.rating) if offer.rating is not None else None,
                "review_count": int(offer.review_count or 0),
                "last_checked_at": offer.last_checked_at,
                "updated_at": offer.updated_at,
                "is_available": available,
                "is_best_offer": offer.is_best_offer,
                "url": offer.url,
                "shipping_method": _value(offer, "shipping_method"),
                "delivery_text": _value(offer, "delivery_text"),
                "warranty_type": _value(offer, "warranty_type"),
                "campaign_text": _value(offer, "campaign_text"),
                "installment_text": _value(offer, "installment_text"),
                "variant_key": _value(offer, "variant_key"),
                "match_score": float(_value(offer, "match_score", 0) or 0),
                "match_reason": _value(offer, "match_reason"),
                "is_sponsored": bool(_value(offer, "is_sponsored", False)),
                "is_official_seller": bool(_value(offer, "is_official_seller", False)),
                "lifecycle_status": lifecycle,
                "first_seen_at": _value(offer, "first_seen_at"),
                "last_price_change_at": _value(offer, "last_price_change_at"),
            }
        )

    enrich_offer_rankings(offers)

    offers.sort(
        key=lambda item: (
            not item["is_available"],
            item["total_price"] if item["total_price"] > 0 else float("inf"),
            item["store"].casefold(),
            str(item["seller"] or "").casefold(),
        )
    )

    available_offers = [item for item in offers if item["is_available"]]
    best = available_offers[0] if available_offers else None
    best_price = best["total_price"] if best else None
    highest_price = (
        max(item["total_price"] for item in available_offers)
        if available_offers else None
    )
    saving = (
        round(max(highest_price - best_price, 0.0), 2)
        if best_price is not None and highest_price is not None
        else 0.0
    )
    saving_percent = (
        round(saving / highest_price * 100, 2)
        if highest_price and highest_price > 0
        else 0.0
    )

    return {
        "identity_key": group.group_key,
        "identity_source": group.identity_source,
        "product_name": group.canonical_name,
        "brand": group.brand,
        "model": group.model,
        "category": group.category,
        "image": group.image,
        "offer_count": len(available_offers),
        "total_offer_count": len(offers),
        "store_count": len({item["store_code"] or item["store"] for item in available_offers}),
        "best_price": best_price,
        "highest_price": highest_price,
        "saving_amount": saving,
        "saving_percent": saving_percent,
        "best_store": best["store"] if best else None,
        "recommended_offer": next((item for item in offers if item.get("is_recommended")), None),
        "offers": offers,
    }
