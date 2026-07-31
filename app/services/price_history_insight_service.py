from __future__ import annotations

from typing import Any


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_price_history_insight(
    comparison: dict[str, Any],
    history_data: dict[str, Any],
    ai_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Fiyat geçmişini kullanıcıya kısa ve anlaşılır biçimde özetler."""

    current_price = _number(comparison.get("best_price"))
    average_price = _number(history_data.get("average_price"))
    lowest_price = _number(history_data.get("lowest_price"))
    highest_price = _number(history_data.get("highest_price"))
    record_count = int(history_data.get("price_record_count", 0) or 0)

    trend = ai_analysis.get("trend") or {}
    trend_code = trend.get("code") or "unknown"
    trend_change = _number(trend.get("change_percent"))

    average_difference_percent = 0.0
    lowest_distance_percent = 0.0
    range_position_percent = 0.0

    if current_price > 0 and average_price > 0:
        average_difference_percent = (
            (current_price - average_price)
            / average_price
            * 100
        )

    if current_price > 0 and lowest_price > 0:
        lowest_distance_percent = (
            (current_price - lowest_price)
            / lowest_price
            * 100
        )

    if highest_price > lowest_price > 0 and current_price > 0:
        range_position_percent = (
            (current_price - lowest_price)
            / (highest_price - lowest_price)
            * 100
        )
        range_position_percent = max(
            0.0,
            min(range_position_percent, 100.0),
        )

    cards: list[dict[str, Any]] = []

    if trend_code == "falling":
        cards.append(
            {
                "icon": "↓",
                "label": "Son fiyat eğilimi",
                "value": f"%{abs(trend_change):.1f} düşüş",
                "type": "success",
            }
        )
    elif trend_code == "rising":
        cards.append(
            {
                "icon": "↑",
                "label": "Son fiyat eğilimi",
                "value": f"%{abs(trend_change):.1f} yükseliş",
                "type": "danger",
            }
        )
    elif trend_code == "stable":
        cards.append(
            {
                "icon": "→",
                "label": "Son fiyat eğilimi",
                "value": "Fiyat stabil",
                "type": "secondary",
            }
        )
    else:
        cards.append(
            {
                "icon": "–",
                "label": "Son fiyat eğilimi",
                "value": "Veri yetersiz",
                "type": "secondary",
            }
        )

    if average_price > 0:
        if average_difference_percent < -0.5:
            average_value = (
                f"Ortalamadan %{abs(average_difference_percent):.1f} ucuz"
            )
            average_type = "success"
        elif average_difference_percent > 0.5:
            average_value = (
                f"Ortalamadan %{average_difference_percent:.1f} pahalı"
            )
            average_type = "warning"
        else:
            average_value = "Geçmiş ortalamaya yakın"
            average_type = "secondary"
    else:
        average_value = "Veri yetersiz"
        average_type = "secondary"

    cards.append(
        {
            "icon": "Ø",
            "label": "Geçmiş ortalamaya göre",
            "value": average_value,
            "type": average_type,
        }
    )

    if lowest_price > 0:
        if lowest_distance_percent <= 0.5:
            lowest_value = "Takip edilen en düşük fiyat"
            lowest_type = "success"
        elif lowest_distance_percent <= 3:
            lowest_value = (
                f"En düşükten yalnızca %{lowest_distance_percent:.1f} yüksek"
            )
            lowest_type = "success"
        elif lowest_distance_percent <= 8:
            lowest_value = (
                f"En düşükten %{lowest_distance_percent:.1f} yüksek"
            )
            lowest_type = "warning"
        else:
            lowest_value = (
                f"En düşükten %{lowest_distance_percent:.1f} yüksek"
            )
            lowest_type = "danger"
    else:
        lowest_value = "Veri yetersiz"
        lowest_type = "secondary"

    cards.append(
        {
            "icon": "★",
            "label": "En düşük fiyata yakınlık",
            "value": lowest_value,
            "type": lowest_type,
        }
    )

    cards.append(
        {
            "icon": "#",
            "label": "Analiz edilen veri",
            "value": f"{record_count} fiyat kaydı",
            "type": "secondary",
        }
    )

    if record_count < 3:
        verdict = "Fiyatı değerlendirmek için henüz yeterli geçmiş veri yok."
        verdict_type = "secondary"
        action = "Bir süre daha takip et"
    elif (
        lowest_distance_percent <= 3
        and average_difference_percent <= 0
        and trend_code != "rising"
    ):
        verdict = (
            "Güncel fiyat geçmişin düşük seviyelerinde ve ortalamanın altında."
        )
        verdict_type = "success"
        action = "Şimdi almak mantıklı"
    elif trend_code == "falling" and lowest_distance_percent > 5:
        verdict = (
            "Fiyat düşüyor ancak geçmişin en düşük seviyesine henüz yakın değil."
        )
        verdict_type = "primary"
        action = "Kısa süre daha beklenebilir"
    elif average_difference_percent > 5 or lowest_distance_percent > 12:
        verdict = (
            "Güncel fiyat geçmiş ortalamanın veya en düşük seviyenin üzerinde."
        )
        verdict_type = "warning"
        action = "Daha iyi fiyat bekle"
    elif trend_code == "rising" and lowest_distance_percent <= 5:
        verdict = (
            "Fiyat yükselmeye başlamış olsa da geçmiş düşük seviyelere yakın."
        )
        verdict_type = "warning"
        action = "İhtiyaç varsa değerlendir"
    else:
        verdict = "Fiyat geçmişe göre dengeli bir seviyede görünüyor."
        verdict_type = "primary"
        action = "Fiyat alarmıyla takip et"

    return {
        "cards": cards,
        "verdict": verdict,
        "verdict_type": verdict_type,
        "action": action,
        "record_count": record_count,
        "average_difference_percent": round(
            average_difference_percent,
            2,
        ),
        "lowest_distance_percent": round(
            lowest_distance_percent,
            2,
        ),
        "range_position_percent": round(
            range_position_percent,
            2,
        ),
    }
