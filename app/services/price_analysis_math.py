from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean
from typing import Any


def rounded(value: float | None) -> float | None:
    return round(float(value), 2) if value is not None else None


def percent_change(current: float, reference: float | None) -> float | None:
    if not reference or reference <= 0:
        return None
    return round(((current - reference) / reference) * 100, 2)


def window_stats(rows: list[tuple[float, datetime]], days: int, now: datetime) -> dict[str, Any]:
    cutoff = now - timedelta(days=days)
    prices = [price for price, created_at in rows if created_at >= cutoff and price > 0]
    return {
        "days": days,
        "record_count": len(prices),
        "average": rounded(mean(prices)) if prices else None,
        "lowest": rounded(min(prices)) if prices else None,
        "highest": rounded(max(prices)) if prices else None,
    }
