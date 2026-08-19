from __future__ import annotations
from statistics import mean, pstdev


def predict_price_ranges(prices: list[float], current: float, trend_code: str, record_count: int) -> dict:
    clean = [float(x) for x in prices if x and x > 0]
    if current <= 0:
        return {"days_7": None, "days_30": None, "low": None, "high": None, "confidence": 0}
    recent = clean[-16:] if clean else [current]
    avg = mean(recent)
    vol = (pstdev(recent) / avg) if len(recent) >= 3 and avg else .04
    drift7 = -.012 if trend_code == "falling" else .012 if trend_code == "rising" else -.002
    drift30 = -.028 if trend_code == "falling" else .032 if trend_code == "rising" else -.006
    d7 = current * (1 + drift7)
    d30 = current * (1 + drift30)
    band = max(.025, min(.12, vol * 1.6))
    confidence = min(88, 38 + min(record_count, 15) * 3)
    return {
        "days_7": round(d7, 2), "days_30": round(d30, 2),
        "low": round(d30 * (1-band), 2), "high": round(d30 * (1+band), 2),
        "confidence": confidence,
    }
