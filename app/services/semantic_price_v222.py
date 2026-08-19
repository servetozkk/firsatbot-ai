from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Iterable


PRICE_RE = re.compile(
    r"(?<!\d)(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?|\d{2,6}(?:[.,]\d{1,2})?)\s*(?:TL|₺)(?!\w)",
    flags=re.IGNORECASE,
)

NEGATIVE_TERMS = (
    "ayda", "aylık", "aylik", "taksit", "alışveriş kredisi", "alisveris kredisi",
    "kredi ile", "krediyle", "aylık ödeme", "aylik odeme", "installment",
    "x taksit", "taksitle",
)
POSITIVE_TERMS = (
    "satış fiyat", "satis fiyat", "ürün fiyat", "urun fiyat", "sepette",
    "web'e özel", "webe özel", "özel fiyat", "ozel fiyat", "indirimli fiyat",
    "kampanyalı fiyat", "kampanyali fiyat", "peşin fiyat", "pesin fiyat",
    "fiyatı", "fiyati", "fiyat",
)


def _normalize(value: str) -> str:
    text = unescape(str(value or "")).casefold()
    for a, b in {"ç":"c", "ğ":"g", "ı":"i", "ö":"o", "ş":"s", "ü":"u"}.items():
        text = text.replace(a, b)
    return " ".join(text.split())


def parse_tr_price(raw: str) -> float | None:
    text = str(raw or "").strip().replace(" ", "")
    if not text:
        return None
    text = re.sub(r"[^0-9.,]", "", text)
    if not text:
        return None
    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    elif text.count(".") == 1 and len(text.rsplit(".", 1)[1]) == 3:
        text = text.replace(".", "")
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


@dataclass(frozen=True)
class PriceCandidate:
    price: float
    score: float
    occurrences: int
    positive_contexts: int
    negative_contexts: int
    first_index: int


def rank_price_candidates(text: str, *, min_price: float = 100.0, max_price: float = 1_000_000.0) -> list[PriceCandidate]:
    raw_text = str(text or "")
    buckets: dict[float, dict[str, float | int]] = {}
    previous_price_end = 0
    for match in PRICE_RE.finditer(raw_text):
        price = parse_tr_price(match.group(1))
        if price is None or not (min_price <= price <= max_price):
            previous_price_end = match.end()
            continue
        # "ayda 44.956 TL 121.999 TL" örneğinde AYDA yalnızca ilk
        # fiyatı nitelemelidir. Bu yüzden bağlamı önceki fiyat sınırında keseriz.
        prefix_start = max(previous_price_end, match.start() - 90)
        prefix = _normalize(raw_text[prefix_start:match.start()])
        suffix = _normalize(raw_text[match.end():min(len(raw_text), match.end() + 45)])
        context = f"{prefix} {suffix}".strip()
        neg = sum(1 for term in NEGATIVE_TERMS if _normalize(term) in context)
        pos = sum(1 for term in POSITIVE_TERMS if _normalize(term) in context)
        key = round(price, 2)
        row = buckets.setdefault(key, {"count": 0, "pos": 0, "neg": 0, "first": match.start()})
        row["count"] = int(row["count"]) + 1
        row["pos"] = int(row["pos"]) + pos
        row["neg"] = int(row["neg"]) + neg
        row["first"] = min(int(row["first"]), match.start())
        previous_price_end = match.end()

    ranked: list[PriceCandidate] = []
    for price, row in buckets.items():
        count = int(row["count"])
        pos = int(row["pos"])
        neg = int(row["neg"])
        # Tekrarlanma faydalı kanıt; kredi/taksit bağlamı güçlü negatif kanıt.
        score = count * 3.0 + pos * 5.0 - neg * 11.0
        ranked.append(PriceCandidate(price, score, count, pos, neg, int(row["first"])))

    ranked.sort(key=lambda item: (-item.score, -item.occurrences, item.first_index, item.price))
    return ranked


def choose_semantic_sale_price(
    text: str,
    *,
    selected_price: float | None = None,
    min_price: float = 100.0,
    max_price: float = 1_000_000.0,
) -> tuple[float | None, dict]:
    ranked = rank_price_candidates(text, min_price=min_price, max_price=max_price)
    if not ranked:
        return selected_price, {"changed": False, "reason": "NO_TL_CANDIDATE", "candidates": []}

    best = ranked[0]
    selected = float(selected_price) if selected_price is not None and selected_price > 0 else None
    selected_row = None
    if selected is not None:
        selected_row = min(ranked, key=lambda item: abs(item.price - selected))
        if abs(selected_row.price - selected) > max(1.0, selected * 0.002):
            selected_row = None

    changed = False
    reason = "SEMANTIC_BEST"
    chosen = best.price

    if selected is not None:
        chosen = selected
        reason = "SELECTED_PRICE_RETAINED"
        # Ana fiyat olarak seçilmiş sayı kredi/taksit bağlamında görünüyorsa ve
        # daha güçlü, anlamlı satış fiyatı adayı varsa değiştir.
        selected_is_installment = bool(
            selected_row
            and selected_row.negative_contexts > 0
            and selected_row.negative_contexts >= selected_row.positive_contexts
        )
        materially_different = abs(best.price - selected) / max(selected, 1.0) >= 0.12
        stronger = selected_row is None or best.score >= selected_row.score + 8.0
        if best.price != selected and materially_different and (selected_is_installment or stronger):
            chosen = best.price
            changed = True
            reason = "INSTALLMENT_OR_CREDIT_VALUE_REPLACED"

    return chosen, {
        "changed": changed,
        "reason": reason,
        "selected_price": selected,
        "chosen_price": chosen,
        "candidates": [
            {
                "price": item.price,
                "score": item.score,
                "occurrences": item.occurrences,
                "positive_contexts": item.positive_contexts,
                "negative_contexts": item.negative_contexts,
            }
            for item in ranked[:8]
        ],
    }
