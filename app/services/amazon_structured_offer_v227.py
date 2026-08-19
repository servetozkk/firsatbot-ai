from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

VERSION = "22.7.0"

POSITIVE_PATH_TERMS = (
    "pricetopay", "buyingprice", "offerprice", "currentprice", "saleprice",
    "ourprice", "dealprice", "displayprice", "landedprice", "buybox",
    "buyingoption", "buyingoptions", "offerlisting", "merchantoffer",
    "merchantoffers", "featured_offer", "featuredoffer", "newbuyboxprice",
    "priceamount", "price",
)
NEGATIVE_PATH_TERMS = (
    "installment", "monthly", "month", "financing", "credit", "kredi",
    "coupon", "kupon", "saving", "savings", "discount", "indirim",
    "reward", "points", "puan", "listprice", "basisprice", "wasprice",
    "oldprice", "strike", "strikeprice", "rrp", "emi",
)
CURRENCY_KEYS = (
    "currency", "currencycode", "currency_code", "currency_symbol", "currencysymbol",
)
AMOUNT_KEYS = (
    "amount", "value", "price", "priceamount", "price_amount", "numericprice",
    "rawprice", "pricevalue",
)
FORMATTED_KEYS = (
    "formattedprice", "formatted_price", "displayprice", "display_price",
    "priceformatted", "price_string",
)


@dataclass(frozen=True)
class StructuredOfferCandidate:
    price: float
    score: int
    path: str
    evidence: str


def parse_try_price(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 0 else None

    text = str(value).strip()
    if not text:
        return None
    folded = text.casefold()
    folded = folded.replace("try", "").replace("₺", "").replace("tl", "").strip()
    folded = re.sub(r"\s+", "", folded)

    # 2.399,00 / 121.499 / 2399,00 / 2399.00
    if "," in folded:
        integer, decimal = folded.rsplit(",", 1)
        if decimal.isdigit() and len(decimal) <= 2:
            normalized = integer.replace(".", "") + "." + decimal
        else:
            normalized = folded.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", folded):
        normalized = folded.replace(".", "")
    else:
        normalized = folded

    try:
        number = float(normalized)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _fold(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _path_score(path: tuple[str, ...]) -> int:
    compact = "/".join(_fold(part) for part in path)
    score = 0
    for term in POSITIVE_PATH_TERMS:
        if term in compact:
            score += 24
    for term in NEGATIVE_PATH_TERMS:
        if term in compact:
            score -= 70
    return score


def _currency_status(mapping: dict[str, Any]) -> tuple[bool, bool]:
    """(TRY kanıtı, başka para birimi kanıtı)."""
    seen = []
    for key, value in mapping.items():
        if _fold(key) in {_fold(item) for item in CURRENCY_KEYS}:
            seen.append(str(value or "").casefold().strip())
    if not seen:
        return False, False
    joined = " ".join(seen)
    is_try = any(token in joined for token in ("try", "tl", "₺", "turkish lira"))
    foreign = any(
        token in joined
        for token in ("usd", "$", "eur", "€", "gbp", "£")
    )
    return is_try, foreign and not is_try


def _formatted_currency_evidence(value: Any) -> bool:
    text = str(value or "").casefold()
    return "₺" in text or " tl" in f" {text}" or "try" in text


def collect_structured_candidates(data: Any) -> list[StructuredOfferCandidate]:
    candidates: list[StructuredOfferCandidate] = []

    def walk(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            try_evidence, foreign = _currency_status(node)
            if foreign:
                # Bu objenin para birimi açıkça TRY değilse fiyat adaylarını alma.
                pass
            else:
                base_score = _path_score(path)
                key_map = {_fold(key): key for key in node.keys()}

                # amount/value gibi numeric alanlar, yalnız fiyat bağlamı güçlü
                # veya TRY para birimi açıkça varsa kabul edilir.
                for normalized_key in {_fold(item) for item in AMOUNT_KEYS}:
                    original = key_map.get(normalized_key)
                    if original is None:
                        continue
                    value = node.get(original)
                    price = parse_try_price(value)
                    if price is None:
                        continue
                    local_path = path + (str(original),)
                    score = base_score + _path_score((str(original),))
                    if try_evidence:
                        score += 55
                    if _formatted_currency_evidence(value):
                        score += 45
                    if score >= 45:
                        candidates.append(
                            StructuredOfferCandidate(
                                price=price,
                                score=score,
                                path="/".join(local_path),
                                evidence=f"{original}={value!r}; TRY={try_evidence}",
                            )
                        )

                for normalized_key in {_fold(item) for item in FORMATTED_KEYS}:
                    original = key_map.get(normalized_key)
                    if original is None:
                        continue
                    value = node.get(original)
                    if not _formatted_currency_evidence(value) and not try_evidence:
                        continue
                    price = parse_try_price(value)
                    if price is None:
                        continue
                    local_path = path + (str(original),)
                    score = base_score + 50 + _path_score((str(original),))
                    if try_evidence:
                        score += 45
                    candidates.append(
                        StructuredOfferCandidate(
                            price=price,
                            score=score,
                            path="/".join(local_path),
                            evidence=f"{original}={value!r}; formatted",
                        )
                    )

            for key, value in node.items():
                walk(value, path + (str(key),))
            return

        if isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, path + (str(index),))

    walk(data, ())
    return candidates


def collect_raw_html_candidates(html: str) -> list[StructuredOfferCandidate]:
    text = str(html or "")
    candidates: list[StructuredOfferCandidate] = []

    patterns = (
        re.compile(
            r'"(?P<key>priceToPay|buyingPrice|offerPrice|currentPrice|salePrice|ourPrice|dealPrice|landedPrice)"'
            r'\s*:\s*\{(?P<body>.{0,900}?)\}',
            re.I | re.S,
        ),
        re.compile(
            r'"(?P<key>priceAmount|price_amount|numericPrice)"\s*:\s*'
            r'(?P<amount>\d+(?:\.\d+)?)',
            re.I,
        ),
    )

    for pattern in patterns:
        for match in pattern.finditer(text):
            key = match.groupdict().get("key") or "price"
            block = match.group(0)
            block_folded = block.casefold()
            if any(term in _fold(block_folded) for term in NEGATIVE_PATH_TERMS):
                continue

            amount_text = match.groupdict().get("amount")
            if amount_text is None:
                amount_match = re.search(
                    r'"(?:amount|value|priceAmount|price)"\s*:\s*'
                    r'(?:"(?P<quoted>[^"]+)"|(?P<number>\d+(?:\.\d+)?))',
                    block,
                    re.I,
                )
                if amount_match:
                    amount_text = amount_match.group("quoted") or amount_match.group("number")

            price = parse_try_price(amount_text)
            if price is None:
                continue

            currency_try = bool(
                re.search(
                    r'"(?:currency|currencyCode|currencySymbol)"\s*:\s*"(?:TRY|TL|₺)"',
                    block,
                    re.I,
                )
            )
            score = 75 + _path_score((key,))
            if currency_try:
                score += 55

            # Raw numeric state'te currency yoksa yalnız çok güçlü priceToPay/
            # buyingPrice gibi anahtarları kabul et.
            if not currency_try and _fold(key) not in {
                "pricetopay", "buyingprice", "offerprice", "currentprice",
                "saleprice", "ourprice", "dealprice", "landedprice",
            }:
                continue

            candidates.append(
                StructuredOfferCandidate(
                    price=price,
                    score=score,
                    path=f"raw-html/{key}",
                    evidence=block[:300],
                )
            )

    return candidates


def choose_structured_offer_price(
    *,
    embedded_data: Any,
    raw_html: str,
) -> tuple[float | None, dict[str, Any] | None]:
    candidates = collect_structured_candidates(embedded_data)
    candidates.extend(collect_raw_html_candidates(raw_html))
    if not candidates:
        return None, None

    candidates = [item for item in candidates if item.score >= 70]
    if not candidates:
        return None, None

    candidates.sort(key=lambda item: (-item.score, item.price, item.path))
    best_score = candidates[0].score
    finalists = [item for item in candidates if item.score >= best_score - 8]
    # Aynı güven seviyesinde Amazon'un satılabilir yeni tekliflerinden en düşük
    # toplam ürün fiyatını seçmek karşılaştırma motoru için doğru davranıştır.
    winner = min(finalists, key=lambda item: (item.price, -item.score))
    return winner.price, {
        "price": winner.price,
        "score": winner.score,
        "path": winner.path,
        "evidence": winner.evidence,
        "candidate_count": len(candidates),
    }
