from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.database.models import GlobalOffer, GlobalOfferPriceHistory, GlobalProduct


STORE_NAMES = {
    "turkcellpasaj": "Turkcell Pasaj",
    "trendyol": "Trendyol",
    "hepsiburada": "Hepsiburada",
    "amazon": "Amazon Türkiye",
    "n11": "N11",
    "pazarama": "Pazarama",
    "teknosa": "Teknosa",
    "mediamarkt": "MediaMarkt",
    "vatan": "Vatan Bilgisayar",
    "idefix": "İdefix",
    "pttavm": "PttAVM",
    "beymen": "Beymen",
}


def record_global_offer_price(
    *,
    db,
    offer: GlobalOffer,
    checked_at: datetime | None = None,
    force: bool = False,
) -> GlobalOfferPriceHistory | None:
    price = float(offer.current_price or 0)
    if price <= 0:
        return None

    shipping = float(offer.shipping_price or 0)
    total = price + shipping
    checked_at = checked_at or datetime.utcnow()

    latest = (
        db.query(GlobalOfferPriceHistory)
        .filter(GlobalOfferPriceHistory.global_offer_id == offer.id)
        .order_by(
            GlobalOfferPriceHistory.recorded_at.desc(),
            GlobalOfferPriceHistory.id.desc(),
        )
        .first()
    )

    unchanged = (
        latest is not None
        and round(float(latest.price or 0), 2) == round(price, 2)
        and round(float(latest.shipping_price or 0), 2) == round(shipping, 2)
        and round(float(latest.total_price or 0), 2) == round(total, 2)
        and str(latest.availability or "") == str(offer.availability or "")
    )
    if unchanged and not force:
        return latest

    row = GlobalOfferPriceHistory(
        global_offer_id=offer.id,
        global_product_id=offer.global_product_id,
        global_variant_id=offer.global_variant_id,
        store_code=offer.store_code,
        seller=offer.seller,
        price=price,
        shipping_price=shipping,
        total_price=total,
        availability=offer.availability,
        recorded_at=checked_at,
        created_at=checked_at,
    )
    db.add(row)
    db.flush()
    from app.services.global_price_alert_service import (
        evaluate_global_price_alerts,
    )
    evaluate_global_price_alerts(
        db=db,
        global_product_id=offer.global_product_id,
        global_variant_id=offer.global_variant_id,
    )
    return row


def get_global_price_history(
    *,
    db,
    identity_key: str,
    selected_variant_id: int | None = None,
    days: int | None = None,
) -> dict[str, Any] | None:
    product = (
        db.query(GlobalProduct)
        .filter(GlobalProduct.identity_key == identity_key)
        .first()
    )
    if product is None:
        return None

    offer_query = db.query(GlobalOffer).filter(
        GlobalOffer.global_product_id == product.id
    )
    if selected_variant_id is not None:
        offer_query = offer_query.filter(
            GlobalOffer.global_variant_id == selected_variant_id
        )
    offers = offer_query.order_by(GlobalOffer.id.asc()).all()

    if not offers:
        return {
            "identity_key": identity_key,
            "product_name": product.canonical_name,
            "store_count": 0,
            "price_record_count": 0,
            "lowest_price": None,
            "highest_price": None,
            "average_price": None,
            "stores": [],
            "data_source": "global_catalog_v9",
            "selected_variant_id": selected_variant_id,
        }

    offer_ids = [offer.id for offer in offers]
    history_query = db.query(GlobalOfferPriceHistory).filter(
        GlobalOfferPriceHistory.global_offer_id.in_(offer_ids)
    )
    if days is not None:
        history_query = history_query.filter(
            GlobalOfferPriceHistory.recorded_at
            >= datetime.utcnow() - timedelta(days=max(1, int(days)))
        )

    rows = history_query.order_by(
        GlobalOfferPriceHistory.recorded_at.asc(),
        GlobalOfferPriceHistory.id.asc(),
    ).all()

    grouped: dict[int, list[GlobalOfferPriceHistory]] = {
        offer.id: [] for offer in offers
    }
    for row in rows:
        grouped.setdefault(row.global_offer_id, []).append(row)

    stores: list[dict[str, Any]] = []
    all_prices: list[float] = []

    for offer in offers:
        history = []
        for row in grouped.get(offer.id, []):
            total = float(row.total_price or row.price or 0)
            if total <= 0:
                continue
            all_prices.append(total)
            history.append(
                {
                    "price": round(total, 2),
                    "product_price": round(float(row.price or 0), 2),
                    "shipping_price": round(float(row.shipping_price or 0), 2),
                    "availability": row.availability,
                    "created_at": (
                        row.recorded_at.isoformat()
                        if row.recorded_at
                        else None
                    ),
                }
            )

        current_total = (
            float(offer.current_price or 0)
            + float(offer.shipping_price or 0)
        )
        if current_total > 0:
            all_prices.append(current_total)

        values = [item["price"] for item in history]
        if current_total > 0:
            values.append(current_total)

        first_price = values[0] if values else None
        last_price = values[-1] if values else None
        change_amount = (
            last_price - first_price
            if first_price is not None and last_price is not None
            else None
        )

        stores.append(
            {
                "offer_id": offer.id,
                "store": STORE_NAMES.get(
                    offer.store_code,
                    offer.store_code.title(),
                ),
                "store_code": offer.store_code,
                "seller": offer.seller,
                "current_price": round(current_total, 2),
                "lowest_price": round(min(values), 2) if values else None,
                "highest_price": round(max(values), 2) if values else None,
                "average_price": (
                    round(sum(values) / len(values), 2)
                    if values
                    else None
                ),
                "change_amount": (
                    round(change_amount, 2)
                    if change_amount is not None
                    else None
                ),
                "change_percent": (
                    round(change_amount / first_price * 100, 2)
                    if change_amount is not None and first_price
                    else None
                ),
                "history_count": len(history),
                "history": history,
                "url": offer.url,
                "global_variant_id": offer.global_variant_id,
            }
        )

    current_best = min(
        (item["current_price"] for item in stores if item["current_price"] > 0),
        default=None,
    )
    lowest = min(all_prices) if all_prices else None
    highest = max(all_prices) if all_prices else None
    average = sum(all_prices) / len(all_prices) if all_prices else None

    return {
        "identity_key": identity_key,
        "product_name": product.canonical_name,
        "brand": product.normalized_brand,
        "model": product.model or product.family,
        "store_count": len(stores),
        "price_record_count": len(all_prices),
        "lowest_price": round(lowest, 2) if lowest is not None else None,
        "highest_price": round(highest, 2) if highest is not None else None,
        "average_price": round(average, 2) if average is not None else None,
        "current_best_price": (
            round(current_best, 2) if current_best is not None else None
        ),
        "is_period_low": (
            current_best is not None
            and lowest is not None
            and round(current_best, 2) <= round(lowest, 2)
        ),
        "stores": stores,
        "data_source": "global_catalog_v9",
        "selected_variant_id": selected_variant_id,
        "period_days": days,
    }
