from __future__ import annotations

from app.services.seo_url_service import product_url

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import case, distinct, func

from app.database.models import ProductGroup, ProductOffer, Store

ENGINE_VERSION = "13.4.4"


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _quality(active: int, total: int, shipping: int, delivery: int, official: int, priced: int) -> dict[str, Any]:
    total = max(int(total or 0), 1)
    parts = {
        "active_offer_ratio": round(active / total * 100, 1),
        "shipping_info_ratio": round(shipping / total * 100, 1),
        "delivery_info_ratio": round(delivery / total * 100, 1),
        "official_seller_ratio": round(official / total * 100, 1),
        "valid_price_ratio": round(priced / total * 100, 1),
    }
    score = round(
        parts["active_offer_ratio"] * .30
        + parts["valid_price_ratio"] * .30
        + parts["shipping_info_ratio"] * .15
        + parts["delivery_info_ratio"] * .15
        + parts["official_seller_ratio"] * .10
    )
    label = "Güçlü veri kapsamı" if score >= 80 else "Orta veri kapsamı" if score >= 55 else "Sınırlı veri kapsamı"
    return {"score": max(0, min(100, score)), "label": label, "components": parts}


def list_store_centers(db) -> list[dict[str, Any]]:
    rows = (
        db.query(
            Store,
            func.count(ProductOffer.id).label("total"),
            func.sum(case((ProductOffer.is_active.is_(True), 1), else_=0)).label("active"),
            func.count(distinct(ProductOffer.group_id)).label("products"),
            func.count(distinct(ProductGroup.category)).label("categories"),
            func.min(ProductOffer.current_price).label("min_price"),
            func.max(ProductOffer.current_price).label("max_price"),
            func.sum(case((ProductOffer.shipping_method.isnot(None), 1), else_=0)).label("shipping"),
            func.sum(case((ProductOffer.delivery_text.isnot(None), 1), else_=0)).label("delivery"),
            func.sum(case((ProductOffer.is_official_seller.is_(True), 1), else_=0)).label("official"),
            func.sum(case((ProductOffer.current_price > 0, 1), else_=0)).label("priced"),
        )
        .outerjoin(ProductOffer, ProductOffer.store_id == Store.id)
        .outerjoin(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        .group_by(Store.id)
        .order_by(func.count(ProductOffer.id).desc(), Store.name.asc())
        .all()
    )
    result = []
    for store, total, active, products, categories, min_price, max_price, shipping, delivery, official, priced in rows:
        quality = _quality(active or 0, total or 0, shipping or 0, delivery or 0, official or 0, priced or 0)
        result.append({
            "id": store.id, "code": store.code, "slug": slugify(store.code or store.name), "name": store.name,
            "base_url": store.base_url, "is_active": bool(store.is_active), "offer_count": int(total or 0),
            "active_offer_count": int(active or 0), "product_count": int(products or 0), "category_count": int(categories or 0),
            "lowest_price": _num(min_price), "highest_price": _num(max_price), "quality": quality,
            "detail_url": f"/magaza-merkezi/{slugify(store.code or store.name)}",
        })
    return result


def get_store_center(db, slug: str, limit: int = 80) -> dict[str, Any] | None:
    all_stores = list_store_centers(db)
    summary = next((x for x in all_stores if x["slug"] == slug or slugify(x["name"]) == slug), None)
    if not summary:
        return None
    store = db.query(Store).filter(Store.id == summary["id"]).first()
    rows = (
        db.query(ProductOffer, ProductGroup)
        .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        .filter(ProductOffer.store_id == store.id, ProductOffer.is_active.is_(True))
        .order_by(ProductOffer.current_price.asc())
        .limit(limit)
        .all()
    )
    products = []
    category_counts: dict[str, int] = {}
    for offer, group in rows:
        category = group.category or "Diğer"
        category_counts[category] = category_counts.get(category, 0) + 1
        shipping = _num(offer.shipping_price)
        total_price = _num(offer.current_price) + shipping
        products.append({
            "identity_key": group.group_key, "name": group.canonical_name, "brand": group.brand or "Markasız",
            "category": category, "image": group.image, "price": _num(offer.current_price), "shipping_price": shipping,
            "total_price": total_price, "shipping_method": offer.shipping_method, "delivery_text": offer.delivery_text,
            "campaign_text": offer.campaign_text, "is_official_seller": bool(offer.is_official_seller),
            "product_url": product_url(group.canonical_name, group.group_key), "store_url": offer.url,
        })
    summary["categories"] = sorted(category_counts.items(), key=lambda x: (-x[1], x[0]))
    summary["products"] = products
    summary["engine_version"] = ENGINE_VERSION
    summary["read_only"] = True
    return summary
