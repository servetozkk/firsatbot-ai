from __future__ import annotations

from typing import Any

from app.database.models import ProductGroup, ProductOffer, Store
from app.services.multi_store_service import (
    calculate_offer_total_price,
    is_offer_available,
)


def get_product_comparison(
    db,
    identity_key: str,
) -> dict[str, Any] | None:
    """Ürün grubunun fiyat ve mağaza karşılaştırma özetini üretir."""
    group = (
        db.query(ProductGroup)
        .filter(ProductGroup.group_key == identity_key)
        .first()
    )

    if group is None:
        return None

    rows = (
        db.query(ProductOffer, Store)
        .join(Store, ProductOffer.store_id == Store.id)
        .filter(ProductOffer.group_id == group.id)
        .all()
    )

    offers: list[dict[str, Any]] = []

    for offer, store in rows:
        total_price = float(calculate_offer_total_price(offer))
        available = (
            offer.current_price is not None
            and float(offer.current_price) > 0
            and is_offer_available(offer.availability)
        )

        offers.append(
            {
                "offer_id": offer.id,
                "store": store.name,
                "store_code": store.code,
                "seller": offer.seller,
                "price": float(offer.current_price or 0),
                "shipping_price": float(offer.shipping_price or 0),
                "total_price": round(total_price, 2),
                "availability": offer.availability,
                "is_available": available,
                "is_best_offer": offer.is_best_offer,
                "url": offer.url,
            }
        )

    offers.sort(
        key=lambda item: (
            not item["is_available"],
            item["total_price"],
            item["store"].casefold(),
        )
    )

    available_offers = [
        item for item in offers if item["is_available"]
    ]

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
        "best_price": best_price,
        "highest_price": highest_price,
        "saving_amount": saving,
        "saving_percent": saving_percent,
        "best_store": best["store"] if best else None,
        "offers": offers,
    }
