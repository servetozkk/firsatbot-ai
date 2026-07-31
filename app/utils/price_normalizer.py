from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable


@dataclass(frozen=True)
class NormalizedPrice:
    value: float
    raw: str


class PriceNormalizer:
    """Turkish and common marketplace price formats -> float.

    The normalizer deliberately does not extract arbitrary numbers from product
    titles. Callers should pass a price field, a currency-labelled text, or a
    list of price-node candidates.
    """

    _currency_re = re.compile(r"(?:₺|\bTL\b|\bTRY\b)", re.IGNORECASE)
    _number_re = re.compile(r"-?\d[\d\s.,]*")

    @classmethod
    def normalize(cls, value: object) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float, Decimal)):
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError):
                return None
            return number if math.isfinite(number) and number > 0 else None

        raw = str(value).replace("\xa0", " ").strip()
        if not raw:
            return None
        match = cls._number_re.search(raw)
        if not match:
            return None
        text = re.sub(r"\s+", "", match.group(0))
        if not text or text.startswith("-"):
            return None

        comma = text.rfind(",")
        dot = text.rfind(".")
        decimal_sep: str | None = None
        if comma >= 0 and dot >= 0:
            decimal_sep = "," if comma > dot else "."
        elif comma >= 0:
            tail = len(text) - comma - 1
            decimal_sep = "," if tail in (1, 2) else None
        elif dot >= 0:
            tail = len(text) - dot - 1
            decimal_sep = "." if tail in (1, 2) else None

        if decimal_sep:
            thousands_sep = "." if decimal_sep == "," else ","
            text = text.replace(thousands_sep, "")
            if text.count(decimal_sep) > 1:
                head, tail = text.rsplit(decimal_sep, 1)
                head = head.replace(decimal_sep, "")
                text = f"{head}.{tail}"
            else:
                text = text.replace(decimal_sep, ".")
        else:
            text = text.replace(".", "").replace(",", "")

        try:
            number = float(Decimal(text))
        except (InvalidOperation, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) and number > 0 else None

    @classmethod
    def extract_currency_prices(cls, text: object) -> list[NormalizedPrice]:
        raw = str(text or "").replace("\xa0", " ")
        if not raw:
            return []
        patterns = (
            re.compile(r"(?:₺|\bTL\b|\bTRY\b)\s*(\d[\d\s.,]*)", re.I),
            re.compile(r"(\d[\d\s.,]*)\s*(?:₺|\bTL\b|\bTRY\b)", re.I),
        )
        result: list[NormalizedPrice] = []
        seen: set[float] = set()
        for pattern in patterns:
            for match in pattern.finditer(raw):
                value = cls.normalize(match.group(1))
                if value is not None and value not in seen:
                    seen.add(value)
                    result.append(NormalizedPrice(value=value, raw=match.group(0).strip()))
        return result

    @classmethod
    def select_offer_prices(
        cls,
        candidates: Iterable[object],
        *,
        fallback: object = None,
        minimum: float = 1.0,
        maximum: float = 100_000_000.0,
    ) -> tuple[float | None, float | None]:
        values: list[float] = []
        for candidate in candidates:
            currency_values = cls.extract_currency_prices(candidate)
            if currency_values:
                values.extend(item.value for item in currency_values)
                continue
            value = cls.normalize(candidate)
            if value is not None:
                values.append(value)
        if not values and fallback is not None:
            values.extend(item.value for item in cls.extract_currency_prices(fallback))

        cleaned: list[float] = []
        for value in values:
            if minimum <= value <= maximum and not any(abs(value - seen) < 0.001 for seen in cleaned):
                cleaned.append(value)
        if not cleaned:
            return None, None
        # Marketplace cards commonly contain current + crossed-out old price.
        # The current price is normally the lower value.
        current = min(cleaned)
        old_candidates = [value for value in cleaned if value > current]
        old = max(old_candidates) if old_candidates else None
        return current, old
