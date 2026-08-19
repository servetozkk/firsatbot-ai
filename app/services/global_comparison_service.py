from __future__ import annotations

from typing import Any

from app.database.models import GlobalOffer, GlobalProduct
from app.services.global_variant_service import get_product_variants


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


def _available(offer: GlobalOffer) -> bool:
    if not offer.is_active or offer.is_hidden:
        return False
    if str(offer.lifecycle_status or "ACTIVE") != "ACTIVE":
        return False
    if float(offer.current_price or 0) <= 0:
        return False
    text = str(offer.availability or "").casefold()
    return not any(
        word in text
        for word in ("stokta yok", "tükendi", "out of stock")
    )


def get_global_product_comparison(
    *,
    db,
    identity_key: str,
    selected_variant_id: int | None = None,
) -> dict[str, Any] | None:
    product = (
        db.query(GlobalProduct)
        .filter(GlobalProduct.identity_key == identity_key)
        .first()
    )
    if product is None:
        return None

    variants = get_product_variants(
        db=db,
        global_product_id=product.id,
        selected_variant_id=selected_variant_id,
    )
    selected_variant_id = variants["selected_variant_id"]

    query = db.query(GlobalOffer).filter(
        GlobalOffer.global_product_id == product.id
    )
    if variants["items"]:
        query = query.filter(
            GlobalOffer.global_variant_id == selected_variant_id
        )
    rows = query.order_by(
        GlobalOffer.current_price.asc(),
        GlobalOffer.id.asc(),
    ).all()

    offers: list[dict[str, Any]] = []
    for row in rows:
        price = float(row.current_price or 0)
        shipping = float(row.shipping_price or 0)
        total = price + shipping
        is_available = _available(row)
        store_name = STORE_NAMES.get(row.store_code, row.store_code.title())

        offers.append(
            {
                "offer_id": row.id,
                "product_id": row.raw_product_id,
                "store_id": None,
                "store_code": row.store_code,
                "store": store_name,
                "seller": row.seller or store_name,
                "url": row.url,
                "price": price,
                "old_price": float(row.old_price or 0),
                "shipping_price": shipping,
                "total_price": total,
                "availability": row.availability or "Bilinmiyor",
                "is_available": is_available,
                "rating": None,
                "review_count": 0,
                "discount_percent": (
                    round(
                        (float(row.old_price) - price)
                        / float(row.old_price)
                        * 100,
                        2,
                    )
                    if row.old_price and float(row.old_price) > price
                    else 0.0
                ),
                "shipping_method": (
                    "Ücretsiz kargo" if shipping <= 0 else "Kargo"
                ),
                "delivery_text": row.delivery_text,
                "warranty_type": row.warranty_type,
                "campaign_text": row.campaign_text,
                "installment_text": row.installment_text,
                "currency": row.currency or "TRY",
                "is_sponsored": False,
                "is_official_seller": bool(row.is_official_seller),
                "match_score": 100.0,
                "match_confidence": "high",
                "last_checked_at": row.last_seen_at,
                "updated_at": row.updated_at,
                "lifecycle_status": row.lifecycle_status,
                "is_best_offer": False,
                "is_cheapest": False,
                "is_recommended": False,
                "offer_score": 0.0,
                "ranking_reasons": [],
            }
        )

    available = [item for item in offers if item["is_available"]]
    available.sort(key=lambda item: (item["total_price"], item["store"]))

    prices = [item["total_price"] for item in available]
    best = min(prices) if prices else None
    highest = max(prices) if prices else None
    saving = (
        highest - best
        if best is not None and highest is not None
        else 0.0
    )

    for item in offers:
        if not item["is_available"]:
            continue
        score = 50.0
        reasons: list[str] = []
        if item["total_price"] == best:
            score += 25
            reasons.append("En düşük toplam fiyat")
            item["is_best_offer"] = True
            item["is_cheapest"] = True
            item["is_recommended"] = True
        if item["shipping_price"] <= 0:
            score += 10
            reasons.append("Ücretsiz kargo")
        if item["is_official_seller"]:
            score += 10
            reasons.append("Resmî satıcı")
        if item["delivery_text"]:
            score += 5
            reasons.append("Teslimat bilgisi mevcut")
        item["offer_score"] = min(100.0, score)
        item["ranking_reasons"] = reasons

    return {
        "identity_key": product.identity_key,
        "product_name": product.canonical_name,
        "brand": product.normalized_brand,
        "model": product.model or product.family,
        "category": product.category,
        "image": product.primary_image,
        "offer_count": len(available),
        "total_offer_count": len(offers),
        "store_count": len(
            {item["store_code"] for item in available}
        ),
        "best_price": best,
        "highest_price": highest,
        "saving_amount": round(saving, 2),
        "saving_percent": (
            round(saving / highest * 100, 2)
            if highest and saving > 0
            else 0.0
        ),
        "best_store": available[0]["store"] if available else None,
        "best_offer": available[0] if available else None,
        "offers": offers,
        "variants": variants["items"],
        "selected_variant_id": selected_variant_id,
        "selected_variant": next((item for item in variants["items"] if item["id"] == selected_variant_id), None),
        "has_multiple_variants": variants["has_multiple_variants"],
        "data_source": "global_catalog_v9",
        "global_product_id": product.id,
    }
