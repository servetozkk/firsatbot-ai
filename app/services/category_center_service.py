from __future__ import annotations

from app.services.seo_url_service import product_url

import re
import unicodedata
from urllib.parse import quote, urlencode

from sqlalchemy import func

from app.database.models import ProductGroup, ProductOffer, Store


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("ı", "i")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def category_url(name: str) -> str:
    return f"/kategori/{quote(slugify(name), safe='')}"


def resolve_category(db, slug: str) -> str | None:
    rows = db.query(ProductGroup.category).filter(ProductGroup.category.isnot(None), ProductGroup.category != "").distinct().all()
    for (name,) in rows:
        clean = str(name or "").strip()
        if clean and slugify(clean) == slugify(slug):
            return clean
    return None


def _money(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def list_category_summaries(db) -> list[dict]:
    rows = (
        db.query(
            ProductGroup.category,
            func.count(func.distinct(ProductGroup.id)).label("product_count"),
            func.count(ProductOffer.id).label("offer_count"),
            func.count(func.distinct(ProductGroup.brand)).label("brand_count"),
            func.count(func.distinct(ProductOffer.store_id)).label("store_count"),
            func.min(ProductOffer.current_price).label("lowest_price"),
            func.max(ProductOffer.current_price).label("highest_price"),
            func.max(ProductGroup.image).label("image"),
        )
        .join(ProductOffer, ProductOffer.group_id == ProductGroup.id)
        .filter(ProductGroup.category.isnot(None), ProductGroup.category != "", ProductOffer.current_price > 0)
        .group_by(ProductGroup.category)
        .order_by(func.count(func.distinct(ProductGroup.id)).desc(), ProductGroup.category.asc())
        .all()
    )
    return [
        {
            "name": str(category),
            "slug": slugify(category),
            "url": category_url(category),
            "product_count": int(product_count or 0),
            "offer_count": int(offer_count or 0),
            "brand_count": int(brand_count or 0),
            "store_count": int(store_count or 0),
            "lowest_price": _money(lowest_price),
            "highest_price": _money(highest_price),
            "image": image,
        }
        for category, product_count, offer_count, brand_count, store_count, lowest_price, highest_price, image in rows
    ]


def category_detail(db, category: str, *, sort: str = "price_asc", limit: int = 60) -> dict:
    rows = (
        db.query(
            ProductGroup,
            func.min(ProductOffer.current_price).label("min_price"),
            func.max(ProductOffer.old_price).label("old_price"),
            func.count(ProductOffer.id).label("offer_count"),
            func.count(func.distinct(ProductOffer.store_id)).label("store_count"),
        )
        .join(ProductOffer, ProductOffer.group_id == ProductGroup.id)
        .filter(ProductGroup.category == category, ProductOffer.current_price > 0)
        .group_by(ProductGroup.id)
        .all()
    )
    cards = []
    brands: dict[str, int] = {}
    stores: set[int] = set()
    for group, min_price, old_price, offer_count, store_count in rows:
        price = _money(min_price)
        previous = _money(old_price)
        drop = round(max(0.0, (previous - price) / previous * 100), 2) if previous > price > 0 else 0.0
        brand = str(group.brand or "Markasız")
        brands[brand] = brands.get(brand, 0) + 1
        cards.append({
            "id": group.id,
            "identity_key": group.group_key,
            "name": group.canonical_name,
            "brand": brand,
            "category": category,
            "image": group.image,
            "price": price,
            "old_price": previous,
            "price_drop_percent": drop,
            "offer_count": int(offer_count or 0),
            "store_count": int(store_count or 0),
            "detail_url": product_url(group.canonical_name, group.group_key),
        })
    key = str(sort or "price_asc")
    if key == "price_desc": cards.sort(key=lambda x: (-x["price"], x["name"]))
    elif key == "stores": cards.sort(key=lambda x: (-x["store_count"], x["price"]))
    elif key == "price_drop": cards.sort(key=lambda x: (-x["price_drop_percent"], x["price"]))
    elif key == "newest": cards.sort(key=lambda x: -int(x["id"] or 0))
    else: cards.sort(key=lambda x: (x["price"] <= 0, x["price"], x["name"]))
    cards = cards[: max(1, min(int(limit or 60), 200))]
    offer_stats = (
        db.query(func.count(ProductOffer.id), func.count(func.distinct(ProductOffer.store_id)), func.min(ProductOffer.current_price), func.max(ProductOffer.current_price))
        .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        .filter(ProductGroup.category == category, ProductOffer.current_price > 0)
        .first()
    )
    store_rows = (
        db.query(Store.name, func.count(ProductOffer.id))
        .join(ProductOffer, ProductOffer.store_id == Store.id)
        .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        .filter(ProductGroup.category == category, ProductOffer.current_price > 0)
        .group_by(Store.id)
        .order_by(func.count(ProductOffer.id).desc())
        .limit(8).all()
    )
    return {
        "category": category,
        "slug": slugify(category),
        "cards": cards,
        "product_count": len(rows),
        "offer_count": int((offer_stats or [0])[0] or 0),
        "store_count": int((offer_stats or [0, 0])[1] or 0),
        "lowest_price": _money((offer_stats or [0, 0, 0])[2]),
        "highest_price": _money((offer_stats or [0, 0, 0, 0])[3]),
        "brands": sorted(brands.items(), key=lambda item: (-item[1], item[0]))[:12],
        "stores": [(str(name), int(count or 0)) for name, count in store_rows],
        "filter_url": "/arama?" + urlencode({"category": category}),
        "sort": key,
        "seo": {
            "title": f"{category} Fiyatları ve Modelleri | FırsatAI",
            "description": f"{category} modellerini, güncel mağaza fiyatlarını ve fiyat düşüşlerini karşılaştırın.",
            "canonical": category_url(category),
        },
        "breadcrumb": [("Ana Sayfa", "/"), ("Kategoriler", "/kategoriler"), (category, category_url(category))],
    }
