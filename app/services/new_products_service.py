from __future__ import annotations

from app.services.seo_url_service import product_url

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func

from app.database.models import ProductGroup, ProductOffer, Store

ENGINE_VERSION = "13.5.3"


def _aware(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _first_datetime(*values: Any) -> datetime | None:
    candidates = [_aware(value) for value in values]
    candidates = [value for value in candidates if value is not None]
    return min(candidates) if candidates else None


def resolve_first_seen(group: Any, offer: Any | None = None) -> tuple[datetime | None, str | None]:
    """Resolve the earliest trustworthy catalog timestamp without inventing a date."""
    group_fields = (
        ("created_at", getattr(group, "created_at", None)),
        ("first_seen_at", getattr(group, "first_seen_at", None)),
        ("discovered_at", getattr(group, "discovered_at", None)),
    )
    for source, value in group_fields:
        parsed = _aware(value)
        if parsed is not None:
            return parsed, source

    if offer is not None:
        offer_fields = (
            ("offer_created_at", getattr(offer, "created_at", None)),
            ("offer_first_seen_at", getattr(offer, "first_seen_at", None)),
            ("offer_checked_at", getattr(offer, "checked_at", None)),
        )
        for source, value in offer_fields:
            parsed = _aware(value)
            if parsed is not None:
                return parsed, source

    fallback = _first_datetime(
        getattr(group, "updated_at", None),
        getattr(group, "last_seen_at", None),
    )
    return (fallback, "group_update_fallback") if fallback else (None, None)


def classify_newness(first_seen: datetime | None, now: datetime | None = None) -> dict[str, Any]:
    now = _aware(now) or datetime.now(timezone.utc)
    if first_seen is None:
        return {
            "status": "unknown",
            "label": "Tarih bilinmiyor",
            "age_days": None,
            "is_new": False,
            "confidence": "low",
            "reason": "Ürünün kataloğa ilk eklenme zamanı doğrulanamıyor.",
        }

    age_days = max(0, int((now - first_seen).total_seconds() // 86400))
    if age_days <= 7:
        status, label, confidence = "very_new", "Çok yeni", "high"
    elif age_days <= 30:
        status, label, confidence = "new", "Yeni", "high"
    elif age_days <= 90:
        status, label, confidence = "recent", "Yakın zamanda eklendi", "medium"
    else:
        status, label, confidence = "older", "Daha eski", "high"
    return {
        "status": status,
        "label": label,
        "age_days": age_days,
        "is_new": age_days <= 30,
        "confidence": confidence,
        "reason": f"Katalogda ilk görülmesinin üzerinden {age_days} gün geçti.",
    }


def list_new_products(
    db,
    days: int = 30,
    brand: str | None = None,
    category: str | None = None,
    store: str | None = None,
    sort: str = "newest",
    limit: int = 200,
) -> dict[str, Any]:
    days = max(1, min(int(days or 30), 365))
    limit = max(1, min(int(limit or 200), 1000))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    query = (
        db.query(ProductGroup, ProductOffer, Store)
        .outerjoin(ProductOffer, ProductOffer.group_id == ProductGroup.id)
        .outerjoin(Store, Store.id == ProductOffer.store_id)
    )
    if brand:
        query = query.filter(func.lower(ProductGroup.brand) == brand.lower())
    if category:
        query = query.filter(func.lower(ProductGroup.category) == category.lower())
    if store:
        query = query.filter(func.lower(Store.code) == store.lower())

    rows = query.limit(max(limit * 12, 1200)).all()
    grouped: dict[Any, dict[str, Any]] = {}

    for group, offer, st in rows:
        group_id = getattr(group, "id", None)
        if group_id is None:
            continue
        first_seen, source = resolve_first_seen(group, offer)
        current = grouped.get(group_id)
        if current is None or (first_seen and (current["first_seen"] is None or first_seen < current["first_seen"])):
            current = {
                "group": group,
                "first_seen": first_seen,
                "timestamp_source": source,
                "offers": [],
                "stores": set(),
            }
            grouped[group_id] = current
        if offer is not None:
            current["offers"].append(offer)
        if st is not None:
            current["stores"].add(getattr(st, "name", None) or getattr(st, "code", None) or "Mağaza")

    items: list[dict[str, Any]] = []
    brands: dict[str, int] = {}
    categories: dict[str, int] = {}
    stores: dict[str, int] = {}

    for entry in grouped.values():
        group = entry["group"]
        first_seen = entry["first_seen"]
        if first_seen is None or first_seen < cutoff:
            continue
        newness = classify_newness(first_seen, now)
        valid_prices: list[float] = []
        active_offer_count = 0
        for offer in entry["offers"]:
            if bool(getattr(offer, "is_active", False)):
                active_offer_count += 1
            try:
                price = float(getattr(offer, "current_price", 0) or 0)
            except (TypeError, ValueError):
                price = 0.0
            if price > 0 and bool(getattr(offer, "is_active", False)):
                valid_prices.append(price)

        brand_name = getattr(group, "brand", None) or "Markasız"
        category_name = getattr(group, "category", None) or "Diğer"
        brands[brand_name] = brands.get(brand_name, 0) + 1
        categories[category_name] = categories.get(category_name, 0) + 1
        for store_name in entry["stores"]:
            stores[store_name] = stores.get(store_name, 0) + 1

        items.append({
            "identity_key": getattr(group, "group_key", ""),
            "name": getattr(group, "canonical_name", None) or getattr(group, "name", None) or "Ürün",
            "brand": brand_name,
            "category": category_name,
            "image": getattr(group, "image", None),
            "first_seen_at": first_seen.isoformat(),
            "timestamp_source": entry["timestamp_source"],
            "lowest_price": min(valid_prices) if valid_prices else None,
            "active_offer_count": active_offer_count,
            "store_count": len(entry["stores"]),
            "product_url": product_url(getattr(group, 'canonical_name', ''), getattr(group, 'group_key', '')),
            "compare_url": f"/karsilastir/compare?products={getattr(group, 'group_key', '')}",
            **newness,
        })

    if sort == "price_asc":
        items.sort(key=lambda x: (x["lowest_price"] is None, x["lowest_price"] or 0, -x["first_seen_at"].__len__()))
    elif sort == "stores_desc":
        items.sort(key=lambda x: (-x["store_count"], -x["active_offer_count"], x["name"].lower()))
    else:
        items.sort(key=lambda x: x["first_seen_at"], reverse=True)

    items = items[:limit]
    return {
        "engine_version": ENGINE_VERSION,
        "generated_at": now.isoformat(timespec="seconds"),
        "read_only": True,
        "period_days": days,
        "items": items,
        "total": len(items),
        "brands": sorted(brands.items(), key=lambda x: (-x[1], x[0].lower())),
        "categories": sorted(categories.items(), key=lambda x: (-x[1], x[0].lower())),
        "stores": sorted(stores.items(), key=lambda x: (-x[1], x[0].lower())),
        "filters": {"days": days, "brand": brand, "category": category, "store": store, "sort": sort},
        "disclaimer": "Yeni ürün etiketi kataloğa ilk görülme zamanına dayanır; ürünün piyasaya çıkış tarihi anlamına gelmeyebilir.",
    }
