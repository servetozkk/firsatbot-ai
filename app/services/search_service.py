from sqlalchemy import or_

from app.database.models import (
    ProductGroup,
    ProductOffer,
    Store,
)


def search_products(
    db,
    query: str,
):
    query = query.strip()

    groups = (
        db.query(ProductGroup)
        .filter(
            or_(
                ProductGroup.canonical_name.ilike(f"%{query}%"),
                ProductGroup.normalized_name.ilike(f"%{query}%"),
                ProductGroup.brand.ilike(f"%{query}%"),
                ProductGroup.model.ilike(f"%{query}%"),
            )
        )
        .all()
    )

    results = []

    for group in groups:

        offers = (
            db.query(ProductOffer, Store)
            .join(
                Store,
                ProductOffer.store_id == Store.id,
            )
            .filter(
                ProductOffer.group_id == group.id
            )
            .all()
        )

        if not offers:
            continue

        best_offer = None

        for offer, store in offers:

            if offer.is_best_offer:
                best_offer = (
                    offer,
                    store,
                )
                break

        if best_offer is None:
            best_offer = offers[0]

        offer, store = best_offer

        results.append(
            {
                "identity_key": group.group_key,
                "product_name": group.canonical_name,
                "brand": group.brand,
                "model": group.model,
                "best_price": offer.current_price,
                "best_store": store.name,
                "offer_count": len(offers),
            }
        )

    return {
        "query": query,
        "count": len(results),
        "results": results,
    }
