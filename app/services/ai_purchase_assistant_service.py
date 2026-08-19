from __future__ import annotations

from statistics import mean, pstdev
from typing import Any
from datetime import datetime, timezone

from app.ai.opportunity_score import calculate_opportunity_score
from app.ai.price_predictor import predict_price_ranges
from app.ai.purchase_advisor import build_decision
from app.ai.risk_analyzer import analyze_price_risk
from app.ai.technical_analyzer import analyze_technical_profile
from app.ai.product_summary import build_short_summary


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def _history_prices(history_data: dict[str, Any]) -> list[float]:
    prices: list[float] = []
    for store in history_data.get("stores", []):
        for item in store.get("history", []):
            value = _number(item.get("price"))
            if value > 0:
                prices.append(value)
        current = _number(store.get("current_price"))
        if current > 0:
            prices.append(current)
    return prices


def build_ai_purchase_assistant(
    *,
    comparison: dict[str, Any],
    history_data: dict[str, Any],
    ai_analysis: dict[str, Any],
    group: Any = None,
    feature_headlines: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fiyat, mağaza ve teknik verilerden açıklanabilir satın alma tavsiyesi üretir."""
    current = _number(comparison.get("best_price"))
    low = _number(history_data.get("lowest_price"))
    high = _number(history_data.get("highest_price"))
    average = _number(history_data.get("average_price"))
    offer_count = int(comparison.get("offer_count", 0) or 0)
    saving_percent = _number(comparison.get("saving_percent"))
    record_count = int(history_data.get("price_record_count", 0) or 0)
    prices = _history_prices(history_data)

    distance_to_low = ((current - low) / low * 100) if current > 0 and low > 0 else None
    versus_average = ((current - average) / average * 100) if current > 0 and average > 0 else None
    trend = ai_analysis.get("trend", {}) or {}
    trend_code = str(trend.get("code") or "insufficient")
    trend_change = _number(trend.get("change_percent"))

    score = calculate_opportunity_score(
        current=current,
        low=low,
        average=average,
        offer_count=offer_count,
        saving_percent=saving_percent,
        trend_code=trend_code,
        base_score=_number(ai_analysis.get("score"), 50),
    )

    risk = analyze_price_risk(prices, trend_code, current)
    decision = build_decision(score, record_count, risk["increase_risk"])
    verdict_code = decision["code"]
    verdict_label = decision["label"]

    verdict_summary = {
        "buy": "Fiyat seviyesi ve geçmiş hareketler satın alma yönünde güçlü sinyal veriyor.",
        "consider": "Fiyat makul seviyede; mağaza koşullarını karşılaştırarak değerlendirebilirsin.",
        "watch": "Acil değilse kısa süre takip edip hedef fiyat alarmı kurmak mantıklı.",
        "wait": "Fiyat geçmiş konumuna göre yüksek; daha iyi fırsat beklenebilir.",
    }.get(verdict_code, "Karar için fiyat geçmişinin biraz daha oluşması gerekiyor.")

    reasons: list[str] = []
    if distance_to_low is not None:
        if distance_to_low <= 3:
            reasons.append(f"Güncel fiyat takip edilen en düşük seviyeye yalnızca %{distance_to_low:.1f} uzaklıkta.")
        else:
            reasons.append(f"Güncel fiyat geçmiş en düşük seviyenin %{distance_to_low:.1f} üzerinde.")
    if versus_average is not None:
        direction = "altında" if versus_average < 0 else "üzerinde"
        reasons.append(f"Fiyat geçmiş ortalamanın %{abs(versus_average):.1f} {direction}.")
    if trend_code == "falling":
        reasons.append(f"Son fiyat hareketlerinde yaklaşık %{abs(trend_change):.1f} düşüş eğilimi var.")
    elif trend_code == "rising":
        reasons.append(f"Son fiyat hareketlerinde yaklaşık %{abs(trend_change):.1f} yükseliş görülüyor.")
    elif trend_code == "stable":
        reasons.append("Son fiyat hareketleri büyük ölçüde stabil.")
    if offer_count:
        reasons.append(f"Ürün şu anda {offer_count} aktif mağaza teklifinde karşılaştırılıyor.")
    if saving_percent > 0:
        reasons.append(f"Mağazalar arasındaki fiyat farkı yaklaşık %{saving_percent:.1f} seviyesinde.")

    forecast = predict_price_ranges(prices, current, trend_code, record_count)
    confidence = min(95, 40 + min(record_count, 12) * 4 + min(offer_count, 5) * 3)
    technical = analyze_technical_profile(group, feature_headlines)
    short_summary = build_short_summary(group, score, verdict_code, technical) if group is not None else verdict_summary

    target_discount = 0.03 if verdict_code in {"buy", "consider"} else 0.07 if verdict_code == "watch" else 0.12
    suggested_target = round(current * (1 - target_discount), 2) if current else None

    # v13.1: karar tutarlılığı, veri kalitesi ve uygulanabilir aksiyon planı
    if record_count < 3:
        data_quality = "Sınırlı"
        data_quality_note = "Fiyat geçmişi az; sonuç ön değerlendirme olarak gösteriliyor."
    elif record_count < 10:
        data_quality = "Orta"
        data_quality_note = "Karar için yeterli veri var, ancak daha uzun geçmiş güveni artırır."
    else:
        data_quality = "Güçlü"
        data_quality_note = "Karar yeterli fiyat geçmişi ve mağaza verisiyle destekleniyor."

    if verdict_code == "buy":
        primary_action = "En ucuz güvenilir mağazayı seç ve satın al"
        timing = "Şimdi"
    elif verdict_code == "consider":
        primary_action = "Mağaza koşullarını karşılaştır ve ihtiyaca göre karar ver"
        timing = "Bugün değerlendir"
    elif verdict_code == "watch":
        primary_action = "Hedef fiyat alarmı kur ve kısa süre takip et"
        timing = f"{decision['wait_days'] or 7} gün izle"
    else:
        primary_action = "Daha iyi fiyat için bekle ve alarm kur"
        timing = f"{decision['wait_days'] or 14} gün izle"

    scenario = {
        "best_case": forecast.get("low"),
        "expected_7d": forecast.get("days_7"),
        "expected_30d": forecast.get("days_30"),
        "risk_case": forecast.get("high"),
    }

    freshness_label = "Güncel" if record_count else "Veri bekleniyor"
    decision_consistency = "Tutarlı"
    if verdict_code in {"buy", "consider"} and trend_code == "falling" and score < 85:
        decision_consistency = "Temkinli"
    elif verdict_code in {"watch", "wait"} and trend_code == "rising":
        decision_consistency = "Yüksek risk"

    generated_at = datetime.now(timezone.utc).isoformat()

    return {
        "score": score,
        "verdict_code": verdict_code,
        "verdict_label": verdict_label,
        "summary": verdict_summary,
        "short_summary": short_summary,
        "confidence": confidence,
        "reasons": reasons[:6],
        "distance_to_low": round(distance_to_low, 1) if distance_to_low is not None else None,
        "versus_average": round(versus_average, 1) if versus_average is not None else None,
        "trend_code": trend_code,
        "trend_change": round(trend_change, 1),
        "forecast_low": forecast["low"],
        "forecast_high": forecast["high"],
        "forecast_7": forecast["days_7"],
        "forecast_30": forecast["days_30"],
        "forecast_confidence": forecast["confidence"],
        "record_count": record_count,
        "risk": risk,
        "technical": technical,
        "decision_action": decision["action"],
        "wait_days": decision["wait_days"],
        "suggested_target": suggested_target,
        "data_quality": data_quality,
        "data_quality_note": data_quality_note,
        "primary_action": primary_action,
        "timing": timing,
        "scenario": scenario,
        "freshness_label": freshness_label,
        "decision_consistency": decision_consistency,
        "generated_at": generated_at,
        "assistant_version": "13.1",
    }
