from __future__ import annotations

from typing import Any

from app.database.models import (
    OfferPriceHistory,
    ProductGroup,
    ProductOffer,
    Store,
)


def get_product_price_history(
    db,
    identity_key: str,
) -> dict[str, Any] | None:
    """
    Merkezi ürün kimliğine bağlı mağaza tekliflerinin
    fiyat geçmişini ve istatistiklerini döndürür.
    """

    product_group = (
        db.query(ProductGroup)
        .filter(
            ProductGroup.group_key == identity_key
        )
        .first()
    )

    if product_group is None:
        return None

    offer_rows = (
        db.query(ProductOffer, Store)
        .join(
            Store,
            ProductOffer.store_id == Store.id,
        )
        .filter(
            ProductOffer.group_id == product_group.id
        )
        .all()
    )

    stores = []
    all_prices = []

    for offer, store in offer_rows:
        history_rows = (
            db.query(OfferPriceHistory)
            .filter(
                OfferPriceHistory.offer_id
                == offer.id
            )
            .order_by(
                OfferPriceHistory.created_at.asc()
            )
            .all()
        )

        history = []

        for price_record in history_rows:
            price = float(price_record.price)

            all_prices.append(price)

            history.append(
                {
                    "price": round(price, 2),
                    "created_at": (
                        price_record.created_at.isoformat()
                        if price_record.created_at
                        else None
                    ),
                }
            )

        current_price = float(
            offer.current_price or 0
        )

        if current_price > 0:
            all_prices.append(current_price)

        store_prices = [
            item["price"]
            for item in history
        ]

        if current_price > 0:
            store_prices.append(current_price)

        stores.append(
            {
                "offer_id": offer.id,
                "store": store.name,
                "store_code": store.code,
                "seller": offer.seller,
                "current_price": round(
                    current_price,
                    2,
                ),
                "lowest_price": (
                    round(min(store_prices), 2)
                    if store_prices
                    else None
                ),
                "highest_price": (
                    round(max(store_prices), 2)
                    if store_prices
                    else None
                ),
                "history_count": len(history),
                "history": history,
                "url": offer.url,
            }
        )

    average_price = (
        round(
            sum(all_prices) / len(all_prices),
            2,
        )
        if all_prices
        else None
    )

    return {
        "identity_key": product_group.group_key,
        "identity_source": (
            product_group.identity_source
        ),
        "product_name": (
            product_group.canonical_name
        ),
        "brand": product_group.brand,
        "model": product_group.model,
        "store_count": len(stores),
        "price_record_count": len(all_prices),
        "lowest_price": (
            round(min(all_prices), 2)
            if all_prices
            else None
        ),
        "highest_price": (
            round(max(all_prices), 2)
            if all_prices
            else None
        ),
        "average_price": average_price,
        "stores": stores,
    }
