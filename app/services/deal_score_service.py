from __future__ import annotations

from typing import Any


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _limit(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def build_deal_score(
    comparison: dict[str, Any],
    history_data: dict[str, Any],
    ai_analysis: dict[str, Any],
) -> dict[str, Any]:
    """
    Ürünün güncel fiyatını, fiyat geçmişini, mağaza sayısını ve
    indirim güvenilirliğini birlikte değerlendirir.
    """

    best_price = _number(comparison.get("best_price"))
    saving_percent = _number(comparison.get("saving_percent"))
    offer_count = int(comparison.get("offer_count", 0) or 0)
    total_offer_count = int(
        comparison.get("total_offer_count", 0) or 0
    )

    average_price = _number(history_data.get("average_price"))
    lowest_price = _number(history_data.get("lowest_price"))
    history_count = int(
        history_data.get("price_record_count", 0) or 0
    )

    trend = ai_analysis.get("trend") or {}
    fake_discount = ai_analysis.get("fake_discount") or {}

    components: list[dict[str, Any]] = []

    def add(
        code: str,
        label: str,
        points: float,
        description: str,
    ) -> None:
        components.append(
            {
                "code": code,
                "label": label,
                "points": round(points, 1),
                "description": description,
            }
        )

    add(
        "base",
        "Temel ürün puanı",
        30,
        "Ürünün aktif ve karşılaştırılabilir olmasına verilen başlangıç puanı.",
    )

    store_points = min(saving_percent * 1.2, 22) if saving_percent > 0 else 0
    add(
        "store_difference",
        "Mağazalar arası avantaj",
        store_points,
        (
            f"En ucuz ve en pahalı teklif arasında %{saving_percent:.1f} fark var."
            if saving_percent > 0
            else "Mağazalar arasında belirgin fiyat farkı bulunmuyor."
        ),
    )

    average_difference = 0.0
    history_points = 0.0

    if best_price > 0 and average_price > 0:
        average_difference = (
            (average_price - best_price)
            / average_price
            * 100
        )

        if average_difference > 0:
            history_points = min(average_difference * 1.4, 22)
        else:
            history_points = max(average_difference * 0.6, -10)

    add(
        "history_average",
        "Geçmiş fiyat ortalaması",
        history_points,
        (
            f"Güncel fiyat geçmiş ortalamanın %{average_difference:.1f} altında."
            if average_difference > 0
            else (
                f"Güncel fiyat geçmiş ortalamanın %{abs(average_difference):.1f} üstünde."
                if average_difference < 0
                else "Geçmiş ortalamayla karşılaştırmak için veri yetersiz."
            )
        ),
    )

    lowest_points = 0.0
    lowest_description = "En düşük fiyat karşılaştırması için veri yetersiz."

    if best_price > 0 and lowest_price > 0:
        distance = (
            (best_price - lowest_price)
            / lowest_price
            * 100
        )

        if distance <= 0.5:
            lowest_points = 10
            lowest_description = "Güncel fiyat takip edilen en düşük seviyede."
        elif distance <= 3:
            lowest_points = 7
            lowest_description = "Güncel fiyat en düşük seviyeye çok yakın."
        elif distance <= 7:
            lowest_points = 3
            lowest_description = "Güncel fiyat geçmiş düşük seviyelere yakın."
        elif distance >= 15:
            lowest_points = -5
            lowest_description = "Güncel fiyat geçmiş en düşük seviyeden uzak."

    add(
        "lowest_price",
        "En düşük fiyata yakınlık",
        lowest_points,
        lowest_description,
    )

    trend_code = trend.get("code")
    trend_change = _number(trend.get("change_percent"))
    trend_points = 0.0
    trend_description = "Fiyat trendi için yeterli veri yok."

    if trend_code == "falling":
        trend_points = min(5 + abs(trend_change) * 0.5, 10)
        trend_description = (
            f"Son kayıtlarda fiyat %{abs(trend_change):.1f} düştü."
        )
    elif trend_code == "stable":
        trend_points = 4
        trend_description = "Fiyat son kayıtlarda büyük ölçüde stabil."
    elif trend_code == "rising":
        trend_points = max(-5 - trend_change * 0.4, -10)
        trend_description = (
            f"Son kayıtlarda fiyat %{trend_change:.1f} yükseldi."
        )

    add(
        "trend",
        "Fiyat trendi",
        trend_points,
        trend_description,
    )

    if offer_count >= 6:
        market_points = 6
    elif offer_count >= 4:
        market_points = 5
    elif offer_count >= 2:
        market_points = 3
    elif offer_count == 1:
        market_points = 1
    else:
        market_points = 0

    add(
        "market",
        "Mağaza ve stok gücü",
        market_points,
        f"{offer_count} aktif, toplam {total_offer_count} teklif karşılaştırılıyor.",
    )

    risk_points = -18 if fake_discount.get("detected") else 0
    add(
        "discount_risk",
        "İndirim güvenilirliği",
        risk_points,
        (
            fake_discount.get(
                "description",
                "İndirim etiketi dikkatle değerlendirilmelidir.",
            )
            if fake_discount.get("detected")
            else "Belirgin bir sahte indirim riski tespit edilmedi."
        ),
    )

    raw_score = sum(_number(item["points"]) for item in components)
    score = int(round(_limit(raw_score, 0, 100)))

    confidence = 0

    if history_count >= 12:
        confidence += 55
    elif history_count >= 6:
        confidence += 42
    elif history_count >= 3:
        confidence += 28
    elif history_count >= 1:
        confidence += 12

    if offer_count >= 5:
        confidence += 30
    elif offer_count >= 3:
        confidence += 22
    elif offer_count >= 2:
        confidence += 15
    elif offer_count == 1:
        confidence += 7

    if average_price > 0 and lowest_price > 0:
        confidence += 15

    confidence = int(_limit(confidence, 0, 100))

    if confidence >= 75:
        confidence_label = "Yüksek veri güveni"
        confidence_type = "success"
    elif confidence >= 45:
        confidence_label = "Orta veri güveni"
        confidence_type = "warning"
    else:
        confidence_label = "Düşük veri güveni"
        confidence_type = "secondary"

    if score >= 85:
        label = "Çok iyi fırsat"
        recommendation = "Satın almak için güçlü bir fiyat seviyesi."
        status_type = "success"
    elif score >= 70:
        label = "İyi fırsat"
        recommendation = "Satın almak değerlendirilebilir."
        status_type = "primary"
    elif score >= 55:
        label = "Ortalama fırsat"
        recommendation = "Fiyat biraz daha takip edilebilir."
        status_type = "warning"
    elif score >= 40:
        label = "Zayıf fırsat"
        recommendation = "Acele etmeden fiyatı takip etmek daha mantıklı."
        status_type = "secondary"
    else:
        label = "Uygun görünmüyor"
        recommendation = "Daha iyi bir fiyat beklemek mantıklı olabilir."
        status_type = "danger"

    positive = sorted(
        [item for item in components if _number(item["points"]) > 0],
        key=lambda item: _number(item["points"]),
        reverse=True,
    )

    negative = sorted(
        [item for item in components if _number(item["points"]) < 0],
        key=lambda item: _number(item["points"]),
    )

    return {
        "score": score,
        "label": label,
        "recommendation": recommendation,
        "status_type": status_type,
        "confidence": confidence,
        "confidence_label": confidence_label,
        "confidence_type": confidence_type,
        "components": components,
        "positive_components": positive,
        "negative_components": negative,
        "history_count": history_count,
        "offer_count": offer_count,
    }
