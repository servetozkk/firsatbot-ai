from __future__ import annotations

from typing import Any

from app.database.models import ProductGroup
from app.services.ai_comparison_service import (
    build_ai_comparison_analysis,
)
from app.services.comparison_service import (
    get_product_comparison,
)
from app.services.deal_score_service import (
    build_deal_score,
)
from app.services.history_service import (
    get_product_price_history,
)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def get_product_alternatives(
    db,
    current_group: ProductGroup,
    current_comparison: dict[str, Any],
    limit: int = 4,
) -> list[dict[str, Any]]:
    """
    Aynı kategorideki ürünleri fiyat yakınlığı ve fırsat skoruna
    göre sıralayarak kompakt alternatif kartları oluşturur.
    """

    category = (current_group.category or "").strip()

    if not category:
        return []

    current_price = _number(
        current_comparison.get("best_price")
    )

    candidate_groups = (
        db.query(ProductGroup)
        .filter(
            ProductGroup.id != current_group.id,
            ProductGroup.category == category,
        )
        .order_by(ProductGroup.updated_at.desc())
        .limit(30)
        .all()
    )

    candidates: list[dict[str, Any]] = []

    for candidate in candidate_groups:
        try:
            comparison = get_product_comparison(
                db=db,
                identity_key=candidate.group_key,
            )

            if comparison is None:
                continue

            best_price = _number(
                comparison.get("best_price")
            )

            if best_price <= 0:
                continue

            history_data = (
                get_product_price_history(
                    db=db,
                    identity_key=candidate.group_key,
                )
                or {}
            )

            ai_analysis = build_ai_comparison_analysis(
                comparison=comparison,
                history_data=history_data,
            )

            deal_score = build_deal_score(
                comparison=comparison,
                history_data=history_data,
                ai_analysis=ai_analysis,
            )

            if current_price > 0:
                price_difference = best_price - current_price
                price_difference_percent = (
                    price_difference / current_price * 100
                )
                price_distance_percent = abs(
                    price_difference_percent
                )
            else:
                price_difference = 0.0
                price_difference_percent = 0.0
                price_distance_percent = 999.0

            candidates.append(
                {
                    "identity_key": candidate.group_key,
                    "name": candidate.canonical_name,
                    "brand": candidate.brand,
                    "model": candidate.model,
                    "category": candidate.category,
                    "image": candidate.image,
                    "best_price": round(best_price, 2),
                    "offer_count": int(
                        comparison.get("offer_count", 0) or 0
                    ),
                    "saving_percent": round(
                        _number(
                            comparison.get("saving_percent")
                        ),
                        2,
                    ),
                    "deal_score": int(deal_score["score"]),
                    "deal_score_label": deal_score["label"],
                    "deal_score_type": deal_score["status_type"],
                    "confidence": int(deal_score["confidence"]),
                    "price_difference": round(
                        price_difference,
                        2,
                    ),
                    "price_difference_percent": round(
                        price_difference_percent,
                        2,
                    ),
                    "price_distance_percent": round(
                        price_distance_percent,
                        2,
                    ),
                }
            )

        except Exception:
            # Tek bir bozuk alternatif tüm detay sayfasını bozmasın.
            continue

    if not candidates:
        return []

    cheapest_id = min(
        candidates,
        key=lambda item: item["best_price"],
    )["identity_key"]

    best_score_id = max(
        candidates,
        key=lambda item: (
            item["deal_score"],
            item["confidence"],
        ),
    )["identity_key"]

    closest_id = min(
        candidates,
        key=lambda item: item["price_distance_percent"],
    )["identity_key"]

    for item in candidates:
        badges: list[dict[str, str]] = []

        if item["identity_key"] == cheapest_id:
            badges.append(
                {
                    "label": "En ucuz alternatif",
                    "type": "success",
                }
            )

        if item["identity_key"] == best_score_id:
            badges.append(
                {
                    "label": "En iyi fırsat",
                    "type": "primary",
                }
            )

        if item["identity_key"] == closest_id:
            badges.append(
                {
                    "label": "Fiyatı en yakın",
                    "type": "secondary",
                }
            )

        item["badges"] = badges[:2]

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    priority_ids = [
        cheapest_id,
        best_score_id,
        closest_id,
    ]

    for identity_key in priority_ids:
        item = next(
            (
                candidate
                for candidate in candidates
                if candidate["identity_key"] == identity_key
            ),
            None,
        )

        if item and identity_key not in selected_ids:
            selected.append(item)
            selected_ids.add(identity_key)

    remaining = sorted(
        candidates,
        key=lambda item: (
            item["deal_score"],
            -item["price_distance_percent"],
            item["offer_count"],
        ),
        reverse=True,
    )

    for item in remaining:
        if item["identity_key"] in selected_ids:
            continue

        selected.append(item)
        selected_ids.add(item["identity_key"])

        if len(selected) >= limit:
            break

    return selected[:limit]
