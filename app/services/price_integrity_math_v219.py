from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

LOW_RATIO = 0.35
HIGH_RATIO = 2.75
MIN_PEER_COUNT = 2


@dataclass(frozen=True, slots=True)
class PriceIntegrityDecision:
    trusted: bool
    status: str
    reason: str
    reference_price: float | None
    ratio: float | None
    peer_count: int
    evidence_prices: tuple[float, ...]


def decide_price_integrity(*, candidate_price: float, evidence_prices: Iterable[float]) -> PriceIntegrityDecision:
    price = float(candidate_price or 0)
    evidence = tuple(float(v) for v in evidence_prices if float(v or 0) > 0)
    if price <= 0:
        return PriceIntegrityDecision(False, "QUARANTINED", "Geçersiz veya sıfır fiyat.", None, None, len(evidence), evidence)
    if len(evidence) < MIN_PEER_COUNT:
        return PriceIntegrityDecision(
            True,
            "TRUSTED_LOW_EVIDENCE",
            "Yeterli karşılaştırma kanıtı yok; fiyat otomatik karantinaya alınmadı.",
            None,
            None,
            len(evidence),
            evidence,
        )
    reference = float(median(evidence))
    ratio = price / reference if reference > 0 else None
    if ratio is not None and ratio < LOW_RATIO:
        return PriceIntegrityDecision(
            False,
            "QUARANTINED",
            f"Fiyat emsal medyanın %{ratio * 100:.1f} seviyesinde; aşırı düşük fiyat anomalisi.",
            reference,
            ratio,
            len(evidence),
            evidence,
        )
    if ratio is not None and ratio > HIGH_RATIO:
        return PriceIntegrityDecision(
            False,
            "QUARANTINED",
            f"Fiyat emsal medyanın {ratio:.2f} katı; aşırı yüksek fiyat anomalisi.",
            reference,
            ratio,
            len(evidence),
            evidence,
        )
    return PriceIntegrityDecision(True, "TRUSTED", "Fiyat emsal aralığıyla uyumlu.", reference, ratio, len(evidence), evidence)
