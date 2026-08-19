from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.database.models import GlobalOffer, GlobalProduct, GlobalProductVariant


def _available(offer: GlobalOffer) -> bool:
    if not offer.is_active or offer.is_hidden:
        return False
    if str(offer.lifecycle_status or "ACTIVE") != "ACTIVE":
        return False
    if float(offer.current_price or 0) <= 0:
        return False
    text = str(offer.availability or "").casefold()
    return not any(value in text for value in ("stokta yok", "tükendi", "out of stock"))


def get_product_variants(*, db, global_product_id: int, selected_variant_id: int | None = None) -> dict[str, Any]:
    product = db.get(GlobalProduct, global_product_id)
    if product is None:
        return {"items": [], "selected_variant_id": None, "has_multiple_variants": False}

    variants = (
        db.query(GlobalProductVariant)
        .filter(GlobalProductVariant.global_product_id == global_product_id)
        .order_by(GlobalProductVariant.id.asc())
        .all()
    )
    offers = db.query(GlobalOffer).filter(GlobalOffer.global_product_id == global_product_id).all()
    offer_map: dict[int | None, list[GlobalOffer]] = defaultdict(list)
    for offer in offers:
        offer_map[offer.global_variant_id].append(offer)

    items: list[dict[str, Any]] = []
    for variant in variants:
        active = [offer for offer in offer_map.get(variant.id, []) if _available(offer)]
        totals = [float(offer.current_price or 0) + float(offer.shipping_price or 0) for offer in active]
        parts = [value for value in (variant.color, variant.network, variant.model_code) if value]
        items.append({
            "id": variant.id,
            "variant_key": variant.variant_key,
            "label": " - ".join(parts) or "Standart",
            "color": variant.color,
            "network": variant.network,
            "model_code": variant.model_code,
            "image": variant.primary_image or product.primary_image,
            "offer_count": len(active),
            "store_count": len({offer.store_code for offer in active}),
            "best_price": min(totals) if totals else None,
            "is_available": bool(active),
        })

    available = [item for item in items if item["is_available"]]
    available.sort(key=lambda item: (item["best_price"] is None, item["best_price"] or 0, item["label"]))
    valid_ids = {item["id"] for item in available}
    if selected_variant_id not in valid_ids:
        selected_variant_id = available[0]["id"] if available else None

    return {
        "items": available,
        "selected_variant_id": selected_variant_id,
        "has_multiple_variants": len(available) > 1,
    }
