from __future__ import annotations

from typing import Any, TYPE_CHECKING

from app.services.product_similarity_service import (
    SimilarityProfile,
    load_feature_maps,
    score_similarity_profiles,
)

if TYPE_CHECKING:
    from app.database.models import ProductGroup


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def build_recommendation_score(
    *,
    similarity_score: float,
    deal_score: float,
    price_difference_percent: float,
    offer_count: int,
    deal_confidence: float,
) -> dict[str, Any]:
    """Açıklanabilir 0-100 öneri puanı üretir.

    Teknik benzerlik ana ağırlıktır. Fırsat kalitesi, fiyat avantajı,
    mağaza kapsamı ve veri güveni skoru destekler.
    """
    similarity_component = _clamp(similarity_score)
    deal_component = _clamp(deal_score)
    confidence_component = _clamp(deal_confidence)
    store_component = _clamp((max(0, int(offer_count)) / 5.0) * 100.0)

    # Aday daha ucuzsa pozitif; %35'ten fazla pahalıysa katkı sıfıra yaklaşır.
    if price_difference_percent <= 0:
        price_component = _clamp(70.0 + abs(price_difference_percent) * 1.5)
    else:
        price_component = _clamp(70.0 - price_difference_percent * 2.0)

    score = (
        similarity_component * 0.55
        + deal_component * 0.20
        + price_component * 0.15
        + store_component * 0.05
        + confidence_component * 0.05
    )
    score = round(_clamp(score), 1)

    if confidence_component < 35 or similarity_component < 45:
        label, code = "Yeterli veri yok", "insufficient_data"
    elif price_difference_percent <= -3 and similarity_component >= 60:
        label, code = "Aynı performans, daha ucuz", "cheaper_same_performance"
    elif deal_component >= 75 and score >= 70:
        label, code = "En iyi fiyat/performans", "best_value"
    elif price_difference_percent >= 3 and price_difference_percent <= 35 and similarity_component >= 65:
        label, code = "Bir üst seviye", "upgrade"
    elif similarity_component >= 58:
        label, code = "Güvenli alternatif", "safe_alternative"
    else:
        label, code = "Yeterli veri yok", "insufficient_data"

    return {
        "score": score,
        "label": label,
        "code": code,
        "components": {
            "technical_similarity": round(similarity_component, 1),
            "deal_quality": round(deal_component, 1),
            "price_value": round(price_component, 1),
            "store_coverage": round(store_component, 1),
            "data_confidence": round(confidence_component, 1),
        },
    }



def build_comparison_highlights(item: dict[str, Any]) -> list[dict[str, str]]:
    """Kart üzerinde gösterilecek kısa ve açıklanabilir teknik/fiyat farklarını üretir."""
    components = item.get("similarity_components") or {}
    highlights: list[dict[str, str]] = []

    price_difference = _number(item.get("price_difference_percent"))
    if price_difference <= -1:
        highlights.append({"type": "positive", "label": f"%{abs(price_difference):.0f} daha ucuz"})
    elif price_difference >= 1:
        highlights.append({"type": "neutral", "label": f"%{price_difference:.0f} daha pahalı"})
    else:
        highlights.append({"type": "neutral", "label": "Benzer fiyat"})

    labels = {
        "ram": "RAM",
        "storage": "Depolama",
        "gpu": "GPU",
        "cpu": "İşlemci",
        "screen": "Ekran",
        "network": "Şebeke",
    }
    for key in ("gpu", "cpu", "ram", "storage", "screen", "network"):
        score = _number(components.get(key), -1)
        if score < 0:
            continue
        if score >= 90:
            highlights.append({"type": "match", "label": f"{labels[key]} aynı"})
        elif score >= 65:
            highlights.append({"type": "neutral", "label": f"{labels[key]} yakın"})
        elif score < 25:
            highlights.append({"type": "warning", "label": f"{labels[key]} farklı"})
        if len(highlights) >= 4:
            break

    if int(item.get("offer_count", 0) or 0) >= 3 and len(highlights) < 4:
        highlights.append({"type": "match", "label": f"{item['offer_count']} mağaza"})
    return highlights[:4]

def _reason_for(item: dict[str, Any], bucket: str) -> str:
    technical = item.get("similarity_reasons") or []
    prefix = technical[0] if technical else f"Teknik benzerlik %{item['similarity_score']:.0f}"
    if bucket == "cheaper":
        return f"{prefix}; %{abs(item['price_difference_percent']):.0f} daha ucuz."
    if bucket == "upgrade":
        return f"{prefix}; yaklaşık %{item['price_difference_percent']:.0f} fiyat farkıyla üst seçenek."
    if bucket == "best_value":
        return f"{prefix}; fırsat skoru {item['deal_score']}."
    label = item.get("recommendation_label")
    return f"{prefix}; {label}." if label else prefix + "."


def get_smart_recommendations(
    db,
    current_group: "ProductGroup",
    current_comparison: dict[str, Any],
    per_bucket: int = 4,
) -> dict[str, list[dict[str, Any]]]:
    """Teknik özellik, fiyat ve fırsat puanını birlikte kullanan öneri motoru."""
    from app.database.models import ProductGroup
    from app.services.comparison_service import get_product_comparison
    from app.services.deal_score_service import build_deal_score
    from app.services.history_service import get_product_price_history
    from app.services.ai_comparison_service import build_ai_comparison_analysis

    category = (current_group.category or "").strip()
    if not category:
        return {"cheaper": [], "similar": [], "upgrade": [], "best_value": []}

    current_price = _number(current_comparison.get("best_price"))
    groups = (
        db.query(ProductGroup)
        .filter(ProductGroup.id != current_group.id)
        .order_by(ProductGroup.updated_at.desc())
        .limit(160)
        .all()
    )
    feature_maps = load_feature_maps(db, [current_group.id, *[group.id for group in groups]])
    current_profile = SimilarityProfile(
        group_id=current_group.id,
        identity_key=current_group.group_key,
        name=current_group.canonical_name,
        brand=current_group.brand,
        model=current_group.model,
        category=current_group.category,
        image=current_group.image,
        features=feature_maps.get(current_group.id, {}),
        best_price=current_price,
    )

    items: list[dict[str, Any]] = []
    for candidate in groups:
        try:
            comparison = get_product_comparison(db=db, identity_key=candidate.group_key)
            if not comparison:
                continue
            best_price = _number(comparison.get("best_price"))
            if best_price <= 0:
                continue

            candidate_profile = SimilarityProfile(
                group_id=candidate.id,
                identity_key=candidate.group_key,
                name=candidate.canonical_name,
                brand=candidate.brand,
                model=candidate.model,
                category=candidate.category,
                image=candidate.image,
                features=feature_maps.get(candidate.id, {}),
                best_price=best_price,
            )
            similarity_result = score_similarity_profiles(current_profile, candidate_profile)
            if not similarity_result.get("compatible"):
                continue

            history = get_product_price_history(db=db, identity_key=candidate.group_key) or {}
            ai = build_ai_comparison_analysis(comparison=comparison, history_data=history)
            deal = build_deal_score(comparison=comparison, history_data=history, ai_analysis=ai)
            difference = best_price - current_price if current_price > 0 else 0.0
            difference_percent = difference / current_price * 100 if current_price > 0 else 0.0
            similarity = _number(similarity_result.get("score"))
            recommendation = build_recommendation_score(
                similarity_score=similarity,
                deal_score=_number(deal.get("score")),
                price_difference_percent=difference_percent,
                offer_count=int(comparison.get("offer_count", 0) or 0),
                deal_confidence=_number(deal.get("confidence")),
            )

            items.append({
                "identity_key": candidate.group_key,
                "name": candidate.canonical_name,
                "brand": candidate.brand,
                "model": candidate.model,
                "category": candidate.category,
                "image": candidate.image,
                "best_price": round(best_price, 2),
                "offer_count": int(comparison.get("offer_count", 0) or 0),
                "deal_score": int(deal.get("score", 0) or 0),
                "deal_score_label": deal.get("label") or "Fırsat",
                "price_difference": round(difference, 2),
                "price_difference_percent": round(difference_percent, 2),
                "similarity_score": round(similarity, 1),
                "recommendation_score": recommendation["score"],
                "recommendation_label": recommendation["label"],
                "recommendation_code": recommendation["code"],
                "recommendation_components": recommendation["components"],
                "deal_confidence": int(deal.get("confidence", 0) or 0),
                "deal_confidence_label": deal.get("confidence_label") or "Veri güveni bilinmiyor",
                "similarity_reasons": similarity_result.get("reasons") or [],
                "similarity_components": similarity_result.get("components") or {},
                "feature_coverage": similarity_result.get("feature_coverage", 0),
            })
        except Exception:
            continue

    # Teknik olarak yeterince benzer olmayan ürünler öneri kutularına alınmaz.
    relevant = [item for item in items if item["similarity_score"] >= 45]
    cheaper = [item for item in relevant if current_price > 0 and item["best_price"] < current_price * 0.97]
    cheaper.sort(key=lambda x: (-x["recommendation_score"], x["best_price"]))

    similar = [item for item in relevant if item["similarity_score"] >= 58]
    similar.sort(key=lambda x: (-x["similarity_score"], -x["recommendation_score"]))

    upgrade = [
        item for item in relevant
        if current_price > 0 and current_price * 1.03 <= item["best_price"] <= current_price * 1.35
    ]
    upgrade.sort(key=lambda x: (-x["similarity_score"], x["price_difference_percent"]))

    best_value = sorted(relevant, key=lambda x: (-x["recommendation_score"], -x["deal_score"], -x["offer_count"]))

    result = {
        "cheaper": cheaper[:per_bucket],
        "similar": similar[:per_bucket],
        "upgrade": upgrade[:per_bucket],
        "best_value": best_value[:per_bucket],
    }
    for bucket, bucket_items in result.items():
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in bucket_items:
            if item["identity_key"] in seen:
                continue
            seen.add(item["identity_key"])
            item["recommendation_reason"] = _reason_for(item, bucket)
            item["comparison_highlights"] = build_comparison_highlights(item)
            item["compare_url"] = f"/karsilastir/compare?left={current_group.group_key}&right={item['identity_key']}"
            unique.append(item)
        result[bucket] = unique
    return result
