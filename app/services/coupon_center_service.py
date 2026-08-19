from __future__ import annotations

from app.services.seo_url_service import product_url

import re
from datetime import datetime
from typing import Any

from sqlalchemy import func

from app.database.models import ProductGroup, ProductOffer, Store

ENGINE_VERSION = "13.5.1"

_CODE_PATTERNS = (
    re.compile(r"(?:kupon(?:\s+kodu)?|kod)\s*[:\-]?\s*([A-Z0-9][A-Z0-9_-]{2,24})", re.I),
    re.compile(r"\b([A-Z]{3,}[0-9]{0,4})\b\s+(?:koduyla|kuponuyla)", re.I),
)
_PERCENT_RE = re.compile(r"%\s*(\d{1,2}(?:[.,]\d+)?)\s*(?:indirim|kupon)?", re.I)
_AMOUNT_RE = re.compile(r"(\d{2,6}(?:[.,]\d{1,2})?)\s*(?:TL|₺)\s*(?:indirim|kupon)", re.I)
_MIN_BASKET_RE = re.compile(r"(?:en\s+az|min(?:imum)?|alt\s+limit)\s*(\d{2,7}(?:[.,]\d{1,2})?)\s*(?:TL|₺)", re.I)
_DATE_RE = re.compile(r"(?:son\s+tarih|geçerli(?:lik)?|bitiş)\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)", re.I)


def _num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_number(value: str | None) -> float | None:
    if not value:
        return None
    raw = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _coupon_text(offer: ProductOffer) -> str:
    return " ".join(
        str(x).strip()
        for x in (offer.campaign_text, offer.delivery_text, offer.shipping_method)
        if x and str(x).strip()
    )


def extract_coupon(offer: ProductOffer) -> dict[str, Any] | None:
    text = _coupon_text(offer)
    folded = text.casefold()
    if not text or not any(k in folded for k in ("kupon", "koduyla", "kuponuyla", "indirim kod")):
        return None

    code = None
    for pattern in _CODE_PATTERNS:
        match = pattern.search(text)
        if match:
            candidate = match.group(1).upper()
            if candidate not in {"KUPON", "KOD", "INDIRIM", "İNDİRİM"}:
                code = candidate
                break

    percent_match = _PERCENT_RE.search(text)
    amount_match = _AMOUNT_RE.search(text)
    basket_match = _MIN_BASKET_RE.search(text)
    date_match = _DATE_RE.search(text)

    percent = _parse_number(percent_match.group(1)) if percent_match else None
    amount = _parse_number(amount_match.group(1)) if amount_match else None
    minimum_basket = _parse_number(basket_match.group(1)) if basket_match else None
    valid_until = date_match.group(1) if date_match else None

    if percent is not None and not (0 < percent <= 100):
        percent = None
    if amount is not None and amount <= 0:
        amount = None

    coupon_type = "code" if code else "automatic"
    if percent is not None:
        benefit_label = f"%{percent:g} indirim"
    elif amount is not None:
        benefit_label = f"{amount:g} TL indirim"
    else:
        benefit_label = "Kupon avantajı"

    return {
        "code": code,
        "coupon_type": coupon_type,
        "percent": percent,
        "amount": amount,
        "minimum_basket": minimum_basket,
        "valid_until": valid_until,
        "benefit_label": benefit_label,
        "source_text": text[:240],
        "copyable": bool(code),
    }


def list_coupons(
    db,
    store: str | None = None,
    category: str | None = None,
    coupon_type: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    query = (
        db.query(ProductOffer, ProductGroup, Store)
        .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        .join(Store, Store.id == ProductOffer.store_id)
        .filter(ProductOffer.is_active.is_(True), ProductOffer.current_price > 0)
    )
    if store:
        query = query.filter(func.lower(Store.code) == store.lower())
    if category:
        query = query.filter(func.lower(ProductGroup.category) == category.lower())

    rows = query.order_by(ProductOffer.checked_at.desc()).limit(max(limit * 8, 600)).all()
    items: list[dict[str, Any]] = []
    stores: dict[str, int] = {}
    categories: dict[str, int] = {}
    counts = {"code": 0, "automatic": 0, "percent": 0, "amount": 0}
    seen: set[tuple[Any, ...]] = set()

    for offer, group, st in rows:
        coupon = extract_coupon(offer)
        if not coupon:
            continue
        if coupon_type and coupon.get("coupon_type") != coupon_type:
            continue

        signature = (
            st.id,
            coupon.get("code"),
            coupon.get("percent"),
            coupon.get("amount"),
            coupon.get("minimum_basket"),
            coupon.get("source_text"),
        )
        if signature in seen:
            continue
        seen.add(signature)

        store_key = st.code or st.name
        category_name = group.category or "Diğer"
        stores[store_key] = stores.get(store_key, 0) + 1
        categories[category_name] = categories.get(category_name, 0) + 1
        counts[coupon["coupon_type"]] += 1
        if coupon.get("percent") is not None:
            counts["percent"] += 1
        if coupon.get("amount") is not None:
            counts["amount"] += 1

        current_price = _num(offer.current_price)
        estimated_price = current_price
        if coupon.get("percent") is not None:
            estimated_price = max(0.0, current_price * (1 - coupon["percent"] / 100))
        elif coupon.get("amount") is not None:
            estimated_price = max(0.0, current_price - coupon["amount"])

        items.append(
            {
                "offer_id": offer.id,
                "identity_key": group.group_key,
                "name": group.canonical_name,
                "brand": group.brand or "Markasız",
                "category": category_name,
                "image": group.image,
                "store_code": st.code,
                "store_name": st.name,
                "price": current_price,
                "estimated_coupon_price": round(estimated_price, 2),
                "product_url": product_url(group.canonical_name, group.group_key),
                "store_url": offer.url,
                **coupon,
            }
        )
        if len(items) >= limit:
            break

    return {
        "engine_version": ENGINE_VERSION,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "read_only": True,
        "items": items,
        "counts": counts,
        "stores": sorted(stores.items(), key=lambda x: (-x[1], x[0])),
        "categories": sorted(categories.items(), key=lambda x: (-x[1], x[0])),
        "filters": {"store": store, "category": category, "coupon_type": coupon_type},
        "disclaimer": "Kupon koşulları mağaza tarafından değiştirilebilir; satın almadan önce mağaza sayfasında doğrulayın.",
    }
