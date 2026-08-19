from __future__ import annotations
from typing import Any


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def calculate_opportunity_score(*, current: float, low: float, average: float, offer_count: int,
                                saving_percent: float, trend_code: str, base_score: float = 50) -> int:
    score = float(base_score)
    if current > 0 and low > 0:
        distance = (current - low) / low * 100
        if distance <= 2: score += 14
        elif distance <= 5: score += 9
        elif distance <= 10: score += 3
        elif distance >= 20: score -= 16
        elif distance >= 15: score -= 10
    if current > 0 and average > 0:
        delta = (current - average) / average * 100
        if delta <= -10: score += 12
        elif delta <= -5: score += 8
        elif delta >= 12: score -= 12
        elif delta >= 7: score -= 7
    if offer_count >= 5: score += 7
    elif offer_count >= 3: score += 4
    elif offer_count <= 1: score -= 4
    if saving_percent >= 12: score += 6
    elif saving_percent >= 6: score += 3
    if trend_code == "falling": score += 3
    elif trend_code == "rising": score -= 5
    return clamp(score)
