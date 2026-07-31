from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any

from app.database.models import OfferPriceHistory, ProductGroup, ProductOffer


from app.services.price_analysis_math import percent_change, rounded, window_stats

def build_price_analysis(db, identity_key: str) -> dict[str, Any] | None:
    group = db.query(ProductGroup).filter(ProductGroup.group_key == identity_key).first()
    if group is None:
        return None

    offers = db.query(ProductOffer).filter(ProductOffer.group_id == group.id).all()
    if not offers:
        return {
            "score": 0,
            "label": "Veri yok",
            "summary": "Bu ürün için henüz aktif teklif bulunmuyor.",
            "windows": {},
            "record_count": 0,
        }

    offer_ids = [offer.id for offer in offers]
    history_rows = (
        db.query(OfferPriceHistory)
        .filter(OfferPriceHistory.offer_id.in_(offer_ids))
        .order_by(OfferPriceHistory.created_at.asc())
        .all()
    )

    rows: list[tuple[float, datetime]] = []
    for item in history_rows:
        price = float(item.price or 0)
        if price > 0 and item.created_at:
            rows.append((price, item.created_at))

    now = datetime.utcnow()
    current_prices = [float(offer.current_price) for offer in offers if float(offer.current_price or 0) > 0]
    current = min(current_prices) if current_prices else 0.0

    # Güncel teklifleri analize dahil et; aynı taramada geçmiş kaydı oluşmamış olabilir.
    for price in current_prices:
        rows.append((price, now))

    valid_prices = [price for price, _ in rows if price > 0]
    first_seen = min((created_at for _, created_at in rows), default=None)
    last_change = max((created_at for _, created_at in rows), default=None)

    windows = {days: window_stats(rows, days, now) for days in (7, 30, 90)}
    all_time_average = mean(valid_prices) if valid_prices else None
    all_time_low = min(valid_prices) if valid_prices else None
    all_time_high = max(valid_prices) if valid_prices else None

    avg30 = windows[30]["average"] or all_time_average
    avg90 = windows[90]["average"] or all_time_average
    low90 = windows[90]["lowest"] or all_time_low

    vs_30 = percent_change(current, avg30)
    vs_90 = percent_change(current, avg90)
    distance_to_low = percent_change(current, low90)

    score = 50.0
    if vs_30 is not None:
        score += max(-20.0, min(25.0, -vs_30 * 2.5))
    if vs_90 is not None:
        score += max(-12.0, min(15.0, -vs_90 * 1.5))
    if distance_to_low is not None:
        score += max(-18.0, min(20.0, 20.0 - distance_to_low * 2.0))
    if len(offers) >= 2:
        score += min(8.0, (len(offers) - 1) * 2.0)
    if len(valid_prices) < 3:
        score = min(score, 60.0)

    score_int = max(0, min(100, round(score)))

    if len(valid_prices) < 3:
        label = "Yeni takip"
        summary = "Fiyat puanı için daha fazla geçmiş veri gerekiyor."
    elif score_int >= 90:
        label = "Süper fırsat"
        summary = "Güncel fiyat geçmişin en avantajlı seviyelerinde."
    elif score_int >= 75:
        label = "İyi fiyat"
        summary = "Güncel fiyat geçmiş ortalamaların altında veya en düşük seviyeye yakın."
    elif score_int >= 55:
        label = "Normal fiyat"
        summary = "Fiyat geçmiş aralığına yakın görünüyor."
    else:
        label = "Fiyat yüksek"
        summary = "Güncel fiyat geçmiş ortalamaların üzerinde görünüyor."

    return {
        "score": score_int,
        "label": label,
        "summary": summary,
        "current_price": rounded(current),
        "record_count": len(valid_prices),
        "offer_count": len(offers),
        "all_time_average": rounded(all_time_average),
        "all_time_low": rounded(all_time_low),
        "all_time_high": rounded(all_time_high),
        "first_seen_at": first_seen,
        "last_change_at": last_change,
        "vs_30_percent": vs_30,
        "vs_90_percent": vs_90,
        "distance_to_90_low_percent": distance_to_low,
        "is_90_day_low": bool(distance_to_low is not None and distance_to_low <= 0.5),
        "windows": {
            "7": windows[7],
            "30": windows[30],
            "90": windows[90],
        },
    }
