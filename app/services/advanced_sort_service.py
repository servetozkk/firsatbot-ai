from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SORT_OPTIONS = {
    "relevance": "Önerilen",
    "price_asc": "En düşük fiyat",
    "price_desc": "En yüksek fiyat",
    "stores": "En çok mağaza",
    "price_drop": "Fiyatı en çok düşen",
    "popular": "En popüler",
    "best_value": "En iyi fiyat/performans",
    "newest": "En yeni",
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def _timestamp(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def enrich_sort_metrics(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prices = [_number(item.get("price")) for item in candidates if _number(item.get("price")) > 0]
    min_price = min(prices) if prices else 0.0
    max_price = max(prices) if prices else 0.0
    price_span = max(max_price - min_price, 1.0)

    enriched: list[dict[str, Any]] = []
    for source in candidates:
        item = dict(source)
        current_price = _number(item.get("price"))
        offers = list(item.get("offers") or [])
        old_prices = [
            _number(offer.get("old_price"))
            for offer in offers
            if _number(offer.get("old_price")) > _number(offer.get("price")) > 0
        ]
        reference_old = max(old_prices) if old_prices else 0.0
        price_drop_percent = (
            max(0.0, ((reference_old - current_price) / reference_old) * 100.0)
            if reference_old > current_price > 0
            else 0.0
        )
        relevance = max(0.0, min(100.0, _number(item.get("relevance"))))
        offer_count = max(0, int(_number(item.get("offer_count"))))
        raw_product_count = max(0, int(_number(item.get("raw_product_count"))))
        popularity_score = min(100.0, offer_count * 12.0 + raw_product_count * 2.0 + relevance * 0.35)
        price_advantage = (
            max(0.0, min(100.0, ((max_price - current_price) / price_span) * 100.0))
            if current_price > 0 and max_price > min_price
            else 50.0
        )
        coverage_score = min(100.0, offer_count * 18.0)
        best_value_score = round(
            relevance * 0.40 + price_advantage * 0.35 + coverage_score * 0.15 + min(price_drop_percent * 3.0, 100.0) * 0.10,
            2,
        )
        item.update(
            {
                "price_drop_percent": round(price_drop_percent, 2),
                "popularity_score": round(popularity_score, 2),
                "best_value_score": best_value_score,
                "sort_updated_ts": _timestamp(item.get("updated_at")),
            }
        )
        enriched.append(item)
    return enriched


def sort_candidates(candidates: list[dict[str, Any]], sort_key: str) -> list[dict[str, Any]]:
    key = sort_key if sort_key in SORT_OPTIONS else "relevance"
    rows = enrich_sort_metrics(candidates)
    name_key = lambda item: str(item.get("name") or "").casefold()

    if key == "price_asc":
        rows.sort(key=lambda item: (_number(item.get("price"), float("inf")), name_key(item)))
    elif key == "price_desc":
        rows.sort(key=lambda item: (-_number(item.get("price")), name_key(item)))
    elif key == "stores":
        rows.sort(key=lambda item: (-int(_number(item.get("offer_count"))), -_number(item.get("relevance")), name_key(item)))
    elif key == "price_drop":
        rows.sort(key=lambda item: (-_number(item.get("price_drop_percent")), _number(item.get("price")), name_key(item)))
    elif key == "popular":
        rows.sort(key=lambda item: (-_number(item.get("popularity_score")), -int(_number(item.get("offer_count"))), name_key(item)))
    elif key == "best_value":
        rows.sort(key=lambda item: (-_number(item.get("best_value_score")), _number(item.get("price")), name_key(item)))
    elif key == "newest":
        rows.sort(key=lambda item: (-_number(item.get("sort_updated_ts")), name_key(item)))
    else:
        rows.sort(key=lambda item: (-_number(item.get("relevance")), -int(_number(item.get("offer_count"))), _number(item.get("price")), name_key(item)))
    return rows
