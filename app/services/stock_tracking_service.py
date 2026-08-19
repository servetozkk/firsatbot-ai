from __future__ import annotations

from app.services.seo_url_service import product_url

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from app.database.models import ProductGroup, ProductOffer, Store

ENGINE_VERSION = "13.5.2"

_OUT_PATTERNS = (
    re.compile(r"\b(?:stok(?:ta)?\s*yok|tükendi|tukendi|satışa kapalı|satisa kapali|mevcut değil|mevcut degil|out\s*of\s*stock)\b", re.I),
)
_LOW_PATTERNS = (
    re.compile(r"\b(?:son\s*\d+\s*(?:ürün|urun|adet)|az\s*kaldı|az\s*kaldi|sınırlı\s*stok|sinirli\s*stok|tükenmek\s*üzere|tukenmek\s*uzere|low\s*stock)\b", re.I),
)
_IN_PATTERNS = (
    re.compile(r"\b(?:stokta|hemen\s*kargo|aynı\s*gün\s*kargo|ayni\s*gun\s*kargo|in\s*stock|mevcut)\b", re.I),
)
_QUANTITY_RE = re.compile(r"\b(?:son|yalnızca|yalnizca)\s*(\d{1,3})\s*(?:ürün|urun|adet)\b", re.I)


def _text(offer: Any) -> str:
    fields = (
        "stock_status", "stock_text", "availability", "availability_text",
        "campaign_text", "delivery_text", "shipping_method", "seller_name",
    )
    return " ".join(str(getattr(offer, name, "") or "").strip() for name in fields).strip()


def classify_stock(offer: Any) -> dict[str, Any]:
    """Produce an explainable stock signal without inventing inventory quantities."""
    text = _text(offer)
    is_active = bool(getattr(offer, "is_active", False))
    try:
        price = float(getattr(offer, "current_price", 0) or 0)
    except (TypeError, ValueError):
        price = 0.0

    quantity = None
    match = _QUANTITY_RE.search(text)
    if match:
        quantity = int(match.group(1))

    if any(p.search(text) for p in _OUT_PATTERNS):
        status, label, confidence, reason = "out_of_stock", "Tükendi", "high", "Mağaza metni stok olmadığını belirtiyor."
    elif not is_active:
        status, label, confidence, reason = "out_of_stock", "Tükendi", "medium", "Teklif aktif değil."
    elif any(p.search(text) for p in _LOW_PATTERNS) or (quantity is not None and quantity <= 5):
        status, label, confidence, reason = "low_stock", "Az kaldı", "high", "Mağaza metni sınırlı stok bildiriyor."
    elif any(p.search(text) for p in _IN_PATTERNS):
        status, label, confidence, reason = "in_stock", "Stokta", "high", "Mağaza metni ürünün stokta olduğunu belirtiyor."
    elif is_active and price > 0:
        status, label, confidence, reason = "in_stock", "Stokta", "medium", "Aktif ve geçerli fiyatlı teklif mevcut."
    else:
        status, label, confidence, reason = "unknown", "Bilinmiyor", "low", "Stok durumunu doğrulayacak yeterli veri yok."

    return {
        "status": status,
        "label": label,
        "confidence": confidence,
        "reason": reason,
        "quantity_hint": quantity,
        "source_text": text[:240],
    }


def list_stock_items(
    db,
    status: str | None = None,
    store: str | None = None,
    category: str | None = None,
    limit: int = 250,
) -> dict[str, Any]:
    query = (
        db.query(ProductOffer, ProductGroup, Store)
        .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        .join(Store, Store.id == ProductOffer.store_id)
    )
    if store:
        query = query.filter(func.lower(Store.code) == store.lower())
    if category:
        query = query.filter(func.lower(ProductGroup.category) == category.lower())

    rows = query.order_by(ProductOffer.checked_at.desc()).limit(max(limit * 8, 800)).all()
    items: list[dict[str, Any]] = []
    counts = {"in_stock": 0, "low_stock": 0, "out_of_stock": 0, "unknown": 0}
    stores: dict[str, int] = {}
    categories: dict[str, int] = {}
    seen: set[tuple[Any, ...]] = set()

    for offer, group, st in rows:
        stock = classify_stock(offer)
        counts[stock["status"]] += 1
        if status and stock["status"] != status:
            continue
        signature = (getattr(group, "id", None), getattr(st, "id", None), stock["status"])
        if signature in seen:
            continue
        seen.add(signature)

        store_key = getattr(st, "code", None) or getattr(st, "name", "Mağaza")
        category_name = getattr(group, "category", None) or "Diğer"
        stores[store_key] = stores.get(store_key, 0) + 1
        categories[category_name] = categories.get(category_name, 0) + 1
        try:
            price = float(getattr(offer, "current_price", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0

        checked_at = getattr(offer, "checked_at", None)
        items.append({
            "offer_id": getattr(offer, "id", None),
            "identity_key": getattr(group, "group_key", ""),
            "name": getattr(group, "canonical_name", "Ürün"),
            "brand": getattr(group, "brand", None) or "Markasız",
            "category": category_name,
            "image": getattr(group, "image", None),
            "store_code": getattr(st, "code", None),
            "store_name": getattr(st, "name", "Mağaza"),
            "price": price,
            "product_url": product_url(getattr(group, 'canonical_name', ''), getattr(group, 'group_key', '')),
            "store_url": getattr(offer, "url", None),
            "checked_at": checked_at.isoformat() if hasattr(checked_at, "isoformat") else None,
            **stock,
        })
        if len(items) >= limit:
            break

    return {
        "engine_version": ENGINE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only": True,
        "items": items,
        "counts": counts,
        "stores": sorted(stores.items(), key=lambda x: (-x[1], x[0])),
        "categories": sorted(categories.items(), key=lambda x: (-x[1], x[0])),
        "filters": {"status": status, "store": store, "category": category},
        "disclaimer": "Stok bilgisi mağaza verisinden türetilen anlık bir sinyaldir; satın almadan önce mağazada doğrulayın.",
    }
