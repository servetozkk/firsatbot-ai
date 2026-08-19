from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _age_hours(value: Any) -> float:
    if value is None:
        return 9999.0
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return 9999.0
    if not isinstance(value, datetime):
        return 9999.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - value).total_seconds() / 3600, 0.0)


def enrich_offer_rankings(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available = [o for o in offers if o.get("is_available") and float(o.get("total_price") or 0) > 0]
    prices = [float(o["total_price"]) for o in available]
    low = min(prices) if prices else 0.0
    high = max(prices) if prices else low

    for offer in offers:
        total = float(offer.get("total_price") or 0)
        score = 0.0
        reasons: list[str] = []

        if offer.get("is_available") and total > 0:
            if high > low:
                price_score = 42 * (high - total) / (high - low)
            else:
                price_score = 42
            score += max(0, min(42, price_score))
            if total == low:
                reasons.append("En düşük toplam fiyat")

            shipping = float(offer.get("shipping_price") or 0)
            if shipping <= 0:
                score += 14
                reasons.append("Ücretsiz kargo")
            elif shipping <= 75:
                score += 8
            elif shipping <= 150:
                score += 4

            if offer.get("is_official_seller"):
                score += 12
                reasons.append("Resmî satıcı")

            rating = float(offer.get("rating") or 0)
            if rating > 0:
                score += min(10, rating * 2)

            age = _age_hours(offer.get("last_checked_at") or offer.get("updated_at"))
            if age <= 3:
                score += 10
                reasons.append("Yeni güncellendi")
            elif age <= 12:
                score += 8
            elif age <= 24:
                score += 6
            elif age <= 48:
                score += 3

            match = float(offer.get("match_score") or 0)
            if match >= 95:
                score += 8
                reasons.append("Çok güçlü ürün eşleşmesi")
            elif match >= 85:
                score += 6
            elif match >= 70:
                score += 3

            if offer.get("delivery_text"):
                score += 2
            if offer.get("campaign_text"):
                score += 1
            if offer.get("installment_text"):
                score += 1
            if offer.get("is_sponsored"):
                score -= 2

        offer["offer_score"] = round(max(0, min(100, score)), 1)
        offer["ranking_reasons"] = reasons[:4]
        offer["is_cheapest"] = bool(available and total == low and total > 0)

    ranked = sorted(
        available,
        key=lambda o: (-float(o.get("offer_score") or 0), float(o.get("total_price") or 10**15), int(o.get("offer_id") or 0)),
    )
    for index, offer in enumerate(ranked, start=1):
        offer["recommendation_rank"] = index
        offer["is_recommended"] = index == 1

    return offers
