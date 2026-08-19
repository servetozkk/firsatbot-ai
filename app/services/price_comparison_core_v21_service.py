from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_

from app.database.models import GlobalOffer, GlobalProduct
from app.services.global_comparison_service import STORE_NAMES


DEFAULT_STALE_HOURS = 6


def _utcnow() -> datetime:
    return datetime.utcnow()


def _freshness(last_seen_at: datetime | None, *, stale_hours: int) -> tuple[str, int | None]:
    if last_seen_at is None:
        return "UNKNOWN", None
    age = _utcnow() - last_seen_at
    age_minutes = max(0, int(age.total_seconds() // 60))
    return ("STALE" if age > timedelta(hours=stale_hours) else "FRESH", age_minutes)


def _available(row: GlobalOffer) -> bool:
    if not bool(row.is_active) or bool(row.is_hidden):
        return False
    if str(row.lifecycle_status or "ACTIVE").upper() != "ACTIVE":
        return False
    if float(row.current_price or 0) <= 0:
        return False
    availability = str(row.availability or "").casefold()
    return not any(token in availability for token in ("stokta yok", "tükendi", "out of stock"))


def get_product_price_comparison(
    *,
    db,
    global_product_id: int,
    stale_hours: int = DEFAULT_STALE_HOURS,
    global_variant_id: int | None = None,
) -> dict[str, Any] | None:
    product = db.query(GlobalProduct).filter(GlobalProduct.id == global_product_id).first()
    if product is None:
        return None

    query = db.query(GlobalOffer).filter(GlobalOffer.global_product_id == product.id)
    if global_variant_id is not None:
        query = query.filter(GlobalOffer.global_variant_id == global_variant_id)
    rows = query.order_by(GlobalOffer.current_price.asc(), GlobalOffer.id.asc()).all()
    quarantined_rows = [
        row for row in rows
        if str(row.lifecycle_status or "ACTIVE").upper() == "QUARANTINED"
    ]
    trusted_rows = [
        row for row in rows
        if str(row.lifecycle_status or "ACTIVE").upper() != "QUARANTINED"
    ]

    offers: list[dict[str, Any]] = []
    for row in trusted_rows:
        price = float(row.current_price or 0)
        shipping = float(row.shipping_price or 0)
        total_price = price + shipping
        freshness, age_minutes = _freshness(row.last_seen_at, stale_hours=max(1, stale_hours))
        available = _available(row)
        store_name = STORE_NAMES.get(row.store_code, str(row.store_code or "Mağaza").title())
        offers.append(
            {
                "offer_id": row.id,
                "raw_product_id": row.raw_product_id,
                "global_variant_id": row.global_variant_id,
                "store_code": row.store_code,
                "store": store_name,
                "seller": row.seller or store_name,
                "url": row.url,
                "price": price,
                "shipping_price": shipping,
                "total_price": total_price,
                "currency": row.currency or "TRY",
                "old_price": float(row.old_price or 0),
                "availability": row.availability or "Bilinmiyor",
                "available": available,
                "is_available": available,
                "freshness": freshness,
                "freshness_code": freshness,
                "age_minutes": age_minutes,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                "last_checked_at": row.last_seen_at,
                "updated_at": row.updated_at,
                "campaign_text": row.campaign_text,
                "installment_text": row.installment_text,
                "delivery_text": row.delivery_text,
                "is_official_seller": bool(row.is_official_seller),
                "warranty_type": row.warranty_type,
                "rating": None,
                "review_count": 0,
                "discount_percent": (
                    round((float(row.old_price) - price) / float(row.old_price) * 100, 2)
                    if row.old_price and float(row.old_price) > price
                    else 0.0
                ),
                "is_sponsored": False,
                "match_score": 100.0,
                "match_confidence": "high",
                "is_best_offer": False,
                "is_cheapest": False,
                "is_recommended": False,
                "offer_score": 0.0,
                "ranking_reasons": [],
                "lifecycle_status": row.lifecycle_status or "ACTIVE",
            }
        )

    active = [item for item in offers if item["available"]]
    active.sort(key=lambda item: (item["total_price"], item["store"], item["seller"]))
    fresh_active = [item for item in active if item["freshness"] == "FRESH"]
    pricing_pool = fresh_active or active

    best_offer = pricing_pool[0] if pricing_pool else None
    highest_offer = pricing_pool[-1] if pricing_pool else None

    best_total = best_offer["total_price"] if best_offer else None
    for item in offers:
        if not item["available"]:
            continue
        score = 50.0
        reasons: list[str] = []
        if best_total is not None and item["total_price"] == best_total:
            score += 25.0
            reasons.append("En düşük güncel toplam fiyat" if fresh_active else "En düşük son bilinen toplam fiyat")
            item["is_best_offer"] = True
            item["is_cheapest"] = True
            item["is_recommended"] = True
        if item["shipping_price"] <= 0:
            score += 10.0
            reasons.append("Ücretsiz kargo")
        if item["is_official_seller"]:
            score += 10.0
            reasons.append("Resmî satıcı")
        if item["freshness"] == "FRESH":
            score += 5.0
            reasons.append("Güncel teklif")
        item["offer_score"] = min(100.0, score)
        item["ranking_reasons"] = reasons
    best_price = best_offer["total_price"] if best_offer else None
    highest_price = highest_offer["total_price"] if highest_offer else None
    saving_amount = (
        round(highest_price - best_price, 2)
        if best_price is not None and highest_price is not None
        else 0.0
    )

    store_status: dict[str, dict[str, Any]] = {}
    for item in offers:
        code = item["store_code"]
        bucket = store_status.setdefault(
            code,
            {
                "store_code": code,
                "store": item["store"],
                "offer_count": 0,
                "available_offer_count": 0,
                "fresh_offer_count": 0,
                "status": "NO_ACTIVE_OFFER",
                "last_seen_at": None,
            },
        )
        bucket["offer_count"] += 1
        if item["available"]:
            bucket["available_offer_count"] += 1
        if item["available"] and item["freshness"] == "FRESH":
            bucket["fresh_offer_count"] += 1
        if item["last_seen_at"] and (bucket["last_seen_at"] is None or item["last_seen_at"] > bucket["last_seen_at"]):
            bucket["last_seen_at"] = item["last_seen_at"]

    for bucket in store_status.values():
        if bucket["fresh_offer_count"]:
            bucket["status"] = "ACTIVE"
        elif bucket["available_offer_count"]:
            bucket["status"] = "STALE"

    return {
        "engine": "FIRSATAI_PRICE_COMPARISON_CORE",
        "engine_version": "21.3.0",
        "data_mode": "CATALOG_FIRST_NO_LIVE_SCRAPE",
        "global_product": {
            "id": product.id,
            "identity_key": product.identity_key,
            "identity_source": product.identity_source,
            "name": product.canonical_name,
            "brand": product.normalized_brand,
            "family": product.family,
            "model": product.model,
            "variant": product.variant,
            "ram_gb": product.ram_gb,
            "storage_gb": product.storage_gb,
            "image": product.primary_image,
            "status": product.status,
        },
        "summary": {
            "offer_count": len(active),
            "fresh_offer_count": len(fresh_active),
            "store_count": len({item["store_code"] for item in active}),
            "best_price": best_price,
            "best_store": best_offer["store"] if best_offer else None,
            "highest_price": highest_price,
            "saving_amount": saving_amount,
            "saving_percent": (
                round(saving_amount / highest_price * 100, 2)
                if highest_price and saving_amount > 0
                else 0.0
            ),
            "stale_hours": max(1, stale_hours),
            "pricing_scope": "FRESH_FIRST" if fresh_active else "LAST_KNOWN_ACTIVE",
            "selected_variant_id": global_variant_id,
            "quarantined_offer_count": len(quarantined_rows),
            "price_integrity_engine": "v21.9",
        },
        "best_offer": best_offer,
        "offers": active + [item for item in offers if not item["available"]],
        "stores": sorted(store_status.values(), key=lambda item: item["store"]),
        "repair_endpoint": f"/api/multi-store-repair/v14/products/{product.id}",
    }


def search_global_catalog(*, db, query: str, limit: int = 20) -> list[dict[str, Any]]:
    text = " ".join(str(query or "").split()).strip()
    if not text:
        return []
    safe_limit = max(1, min(int(limit or 20), 50))
    tokens = [token.casefold() for token in text.split() if len(token) >= 2]
    if not tokens:
        return []

    conditions = []
    for token in tokens[:8]:
        like = f"%{token}%"
        conditions.append(
            or_(
                func.lower(GlobalProduct.canonical_name).like(like),
                func.lower(GlobalProduct.normalized_brand).like(like),
                func.lower(GlobalProduct.family).like(like),
                func.lower(GlobalProduct.model).like(like),
                func.lower(GlobalProduct.variant).like(like),
                func.lower(GlobalProduct.model_code).like(like),
            )
        )

    products = (
        db.query(GlobalProduct)
        .filter(GlobalProduct.status == "ACTIVE")
        .filter(*conditions)
        .order_by(GlobalProduct.active_offer_count.desc(), GlobalProduct.updated_at.desc())
        .limit(safe_limit)
        .all()
    )

    result: list[dict[str, Any]] = []
    for product in products:
        offer_rows = (
            db.query(GlobalOffer)
            .filter(GlobalOffer.global_product_id == product.id)
            .filter(GlobalOffer.is_active.is_(True))
            .filter(GlobalOffer.is_hidden.is_(False))
            .all()
        )
        valid_prices = [
            float(row.current_price)
            for row in offer_rows
            if float(row.current_price or 0) > 0 and str(row.lifecycle_status or "ACTIVE").upper() == "ACTIVE"
        ]
        result.append(
            {
                "global_product_id": product.id,
                "identity_key": product.identity_key,
                "name": product.canonical_name,
                "brand": product.normalized_brand,
                "family": product.family,
                "variant": product.variant,
                "ram_gb": product.ram_gb,
                "storage_gb": product.storage_gb,
                "image": product.primary_image,
                "offer_count": len(valid_prices),
                "best_price": min(valid_prices) if valid_prices else None,
                "detail_api": f"/api/price-comparison/v21/products/{product.id}",
                "detail_url": f"/fiyat-karsilastirma/urun/{product.id}",
            }
        )
    return result
