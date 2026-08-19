from __future__ import annotations
from statistics import mean, pstdev


def analyze_price_risk(prices: list[float], trend_code: str, current: float) -> dict:
    clean = [float(x) for x in prices if x and x > 0]
    if len(clean) < 3 or current <= 0:
        return {"increase_risk": 50, "volatility": "Veri az", "volatility_percent": 0.0, "label": "Orta risk"}
    recent = clean[-20:]
    avg = mean(recent)
    vol = (pstdev(recent) / avg * 100) if avg else 0
    risk = 50
    if trend_code == "rising": risk += 22
    elif trend_code == "falling": risk -= 16
    if current < avg * .96: risk += 12
    elif current > avg * 1.08: risk -= 8
    risk += min(12, vol * 1.5)
    risk = max(8, min(92, int(round(risk))))
    if vol < 2.5: volatility = "Düşük"
    elif vol < 6: volatility = "Orta"
    else: volatility = "Yüksek"
    label = "Yüksek yükselme riski" if risk >= 70 else "Orta risk" if risk >= 40 else "Düşük yükselme riski"
    return {"increase_risk": risk, "volatility": volatility, "volatility_percent": round(vol, 1), "label": label}
