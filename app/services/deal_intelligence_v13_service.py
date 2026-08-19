from __future__ import annotations

from typing import Any


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_deal_intelligence_v13(
    price_analysis: dict[str, Any],
    ai_analysis: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    """Deterministik fiyat geçmişinden açıklanabilir fırsat kararı üretir.

    Bu servis yapay zekâ servisine dış istek yapmaz. Mevcut fiyat geçmişi,
    mağaza kapsamı ve trend verilerini kullanıcıya anlaşılır hale getirir.
    """

    score = int(price_analysis.get("score") or 0)
    records = int(price_analysis.get("record_count") or 0)
    offer_count = int(price_analysis.get("offer_count") or comparison.get("offer_count") or 0)
    current = _num(price_analysis.get("current_price") or comparison.get("best_price"))
    average = _num(price_analysis.get("all_time_average"))
    low = _num(price_analysis.get("all_time_low"))
    vs_30 = price_analysis.get("vs_30_percent")
    vs_90 = price_analysis.get("vs_90_percent")

    trend = ai_analysis.get("trend") or {}
    trend_code = str(trend.get("code") or "insufficient")
    trend_change = _num(trend.get("change_percent"))
    trend_map = {
        "falling": ("Düşüyor", "↘", "success"),
        "rising": ("Yükseliyor", "↗", "warning"),
        "stable": ("Sabit", "→", "neutral"),
        "insufficient": ("Veri bekleniyor", "–", "neutral"),
    }
    trend_label, trend_icon, trend_tone = trend_map.get(
        trend_code, trend_map["insufficient"]
    )

    if records < 3:
        confidence = "Düşük"
        confidence_tone = "neutral"
        action = "Fiyat alarmıyla takip et"
        verdict = "Geçmiş veri henüz sınırlı; kesin satın alma kararı için takip önerilir."
    elif score >= 85:
        confidence = "Yüksek"
        confidence_tone = "success"
        action = "Satın almak için güçlü fırsat"
        verdict = "Fiyat geçmişe göre oldukça avantajlı ve en düşük seviyelere yakın."
    elif score >= 70:
        confidence = "Yüksek"
        confidence_tone = "success"
        action = "Satın almak için uygun"
        verdict = "Güncel fiyat geçmiş ortalamaya göre avantajlı görünüyor."
    elif score >= 55:
        confidence = "Orta"
        confidence_tone = "primary"
        action = "İhtiyaca göre değerlendir"
        verdict = "Fiyat dengeli seviyede; acil değilse alarm kurarak izlenebilir."
    else:
        confidence = "Orta"
        confidence_tone = "warning"
        action = "Daha iyi fiyat bekle"
        verdict = "Güncel fiyat geçmiş ortalamaların üzerinde görünüyor."

    if trend_code == "falling" and score < 85 and records >= 3:
        action = "Kısa süre daha beklenebilir"
        verdict = "Fiyat düşüş eğiliminde; yeni bir dip fiyat oluşma ihtimali var."
    elif trend_code == "rising" and score >= 70 and records >= 3:
        action = "İhtiyaç varsa geciktirme"
        verdict = "Fiyat avantajlı fakat yükseliş eğilimi başlamış görünüyor."

    reasons: list[str] = []
    if price_analysis.get("is_90_day_low"):
        reasons.append("Son 90 günün en düşük fiyat seviyesinde")
    if vs_30 is not None:
        value = float(vs_30)
        if value <= -1:
            reasons.append(f"30 günlük ortalamadan %{abs(value):.1f} daha ucuz")
        elif value >= 1:
            reasons.append(f"30 günlük ortalamadan %{value:.1f} daha pahalı")
    if vs_90 is not None:
        value = float(vs_90)
        if value <= -1:
            reasons.append(f"90 günlük ortalamadan %{abs(value):.1f} daha ucuz")
    if offer_count >= 2:
        reasons.append(f"{offer_count} aktif teklif karşılaştırıldı")
    if not reasons:
        reasons.append("Fiyat geçmişi ve mevcut teklifler birlikte değerlendirildi")

    badges: list[dict[str, str]] = []
    if offer_count:
        badges.append({"label": "En iyi fiyat", "icon": "🏆"})
    if price_analysis.get("is_90_day_low"):
        badges.append({"label": "90 günün dibi", "icon": "🔥"})
    if trend_code == "falling":
        badges.append({"label": "Fiyat düşüyor", "icon": "↘"})
    if offer_count >= 3:
        badges.append({"label": "Geniş mağaza seçeneği", "icon": "✓"})

    average_difference = None
    if current > 0 and average > 0:
        average_difference = round((current - average) / average * 100, 2)
    low_difference = None
    if current > 0 and low > 0:
        low_difference = round((current - low) / low * 100, 2)

    return {
        "score": score,
        "score_label": price_analysis.get("label") or "Veri bekleniyor",
        "confidence": confidence,
        "confidence_tone": confidence_tone,
        "action": action,
        "verdict": verdict,
        "reasons": reasons[:4],
        "badges": badges[:4],
        "trend": {
            "code": trend_code,
            "label": trend_label,
            "icon": trend_icon,
            "tone": trend_tone,
            "change_percent": round(trend_change, 2),
        },
        "record_count": records,
        "offer_count": offer_count,
        "average_difference_percent": average_difference,
        "lowest_difference_percent": low_difference,
        "explainable": True,
        "engine_version": "13.0",
    }
