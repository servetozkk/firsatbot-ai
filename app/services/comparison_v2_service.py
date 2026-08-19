from __future__ import annotations

from collections import OrderedDict
from typing import Any

ENGINE_VERSION = "13.4.5"
MAX_PRODUCTS = 4


def _winner_indexes(features: list[dict[str, Any] | None]) -> list[int]:
    present = [(i, f) for i, f in enumerate(features) if f is not None and f.get("raw_value") is not None]
    if len(present) < 2:
        return []
    comparison_type = str(present[0][1].get("comparison_type") or "neutral")
    values = [f.get("raw_value") for _, f in present]
    if comparison_type == "higher_better":
        best = max(values)
    elif comparison_type == "lower_better":
        best = min(values)
    elif comparison_type == "yes_better":
        best = True
    elif comparison_type == "no_better":
        best = False
    else:
        return []
    return [i for i, f in present if f.get("raw_value") == best]


def build_comparison_matrix(feature_maps: list[dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    codes: set[str] = set()
    for fmap in feature_maps:
        codes.update(fmap.keys())
    rows: list[dict[str, Any]] = []
    for code in codes:
        features = [fmap.get(code) for fmap in feature_maps]
        source = next((item for item in features if item is not None), None)
        if source is None:
            continue
        displays = [item.get("display_value") if item else None for item in features]
        normalized = [str(v).strip().casefold() if v is not None else None for v in displays]
        nonempty = [v for v in normalized if v is not None]
        winners = _winner_indexes(features)
        rows.append({
            "code": code,
            "name": source.get("name") or code,
            "section": source.get("section") or "Genel",
            "sort_order": int(source.get("sort_order") or 0),
            "values": displays,
            "winner_indexes": winners,
            "is_different": len(set(nonempty)) > 1 or len(nonempty) != len(displays),
            "is_equal": len(nonempty) == len(displays) and len(set(nonempty)) == 1,
            "is_comparable": str(source.get("comparison_type") or "neutral") in {
                "higher_better", "lower_better", "yes_better", "no_better"
            },
        })
    rows.sort(key=lambda r: (r["section"], r["sort_order"], r["name"]))
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        grouped.setdefault(row["section"], []).append(row)
    return [{
        "name": name,
        "rows": section_rows,
        "different_count": sum(1 for r in section_rows if r["is_different"]),
    } for name, section_rows in grouped.items()]


def build_product_metrics(products: list[Any], summaries: list[dict[str, Any] | None], sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    win_counts = [0] * len(products)
    comparable = 0
    for section in sections:
        for row in section["rows"]:
            if row["is_comparable"]:
                comparable += 1
            for idx in row["winner_indexes"]:
                if idx < len(win_counts):
                    win_counts[idx] += 1
    prices = [float(s.get("best_price")) if s and s.get("best_price") is not None else None for s in summaries]
    valid_prices = [p for p in prices if p is not None and p > 0]
    min_price = min(valid_prices) if valid_prices else None
    max_store_count = max([int(s.get("store_count") or 0) for s in summaries if s] or [0])
    metrics: list[dict[str, Any]] = []
    for idx, product in enumerate(products):
        summary = summaries[idx] or {}
        price = prices[idx]
        store_count = int(summary.get("store_count") or 0)
        price_score = 100.0 if min_price and price == min_price else (min_price / price * 100.0 if min_price and price else 0.0)
        coverage_score = (store_count / max_store_count * 100.0) if max_store_count else 0.0
        technical_score = (win_counts[idx] / max(1, comparable) * 100.0)
        has_market_data = bool((price is not None and price > 0) or store_count > 0)
        value_score = (
            round(min(100.0, price_score * .5 + coverage_score * .2 + technical_score * .3), 1)
            if has_market_data
            else None
        )
        metrics.append({
            "product": product,
            "summary": summary,
            "price": price,
            "store_count": store_count,
            "win_count": win_counts[idx],
            "technical_score": round(technical_score, 1),
            "value_score": value_score,
            "has_market_data": has_market_data,
            "is_cheapest": bool(min_price is not None and price == min_price),
        })
    scored_metrics = [m for m in metrics if m.get("value_score") is not None]
    if scored_metrics:
        best_value = max(m["value_score"] for m in scored_metrics)
        for m in metrics:
            m["is_best_value"] = m.get("value_score") is not None and m["value_score"] == best_value
    else:
        for m in metrics:
            m["is_best_value"] = False
    return metrics


def normalize_selected_keys(products: list[str] | None, left: str | None = None, right: str | None = None) -> list[str]:
    values = list(products or [])
    if left:
        values.insert(0, left)
    if right:
        values.append(right)
    result: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
        if len(result) >= MAX_PRODUCTS:
            break
    return result
