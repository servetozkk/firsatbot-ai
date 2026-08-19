from __future__ import annotations

import re
from typing import Iterable

ENGINE_VERSION = "22.6.0"

POSITIVE_TERMS = (
    "yeni ürün",
    "yeni teklif",
    "satın alma seçenek",
    "tüm satın alma seçenek",
    "öne çıkan teklif yok",
    "new offers",
    "buying options",
    "see all buying options",
    "other sellers",
    "diğer satıcı",
    "fiyat",
)

NEGATIVE_TERMS = (
    "ayda",
    "taksit",
    "aylık",
    "aylik",
    "kredi",
    "kupon",
    "kazanç",
    "kazanc",
    "tasarruf",
    "indirim oran",
    "puan",
    "hediye kart",
)


def parse_try_price(value: str) -> float | None:
    text = str(value or "").strip().casefold()
    text = text.replace("₺", "").replace("tl", "").strip()
    text = re.sub(r"\s+", "", text)
    if not text:
        return None

    # TR: 2.399,00 / 121.499 / 2399,00
    if "," in text:
        integer, decimal = text.rsplit(",", 1)
        if decimal.isdigit() and len(decimal) <= 2:
            integer = integer.replace(".", "")
            normalized = integer + "." + decimal
        else:
            normalized = text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
        normalized = text.replace(".", "")
    else:
        normalized = text.replace(",", ".")

    try:
        price = float(normalized)
    except ValueError:
        return None
    return price if price > 0 else None


def recover_amazon_price(
    text_blocks: Iterable[tuple[str, int]],
) -> float | None:
    candidates: list[tuple[int, float, str]] = []

    for raw_text, base_score in text_blocks:
        text = " ".join(str(raw_text or "").split())
        if not text:
            continue
        folded = text.casefold()
        score = int(base_score)
        # Blokta hem gerçek fiyat hem de ayrı bir taksit/kredi cümlesi bulunabilir.
        # Bu nedenle negatif terimler bütün bloğu düşürmez; her fiyat adayının
        # yakın bağlamında ayrı ayrı kesin red uygulanır.
        score += 15 * sum(term in folded for term in POSITIVE_TERMS)

        for match in re.finditer(
            r"(?<!\d)(\d{1,3}(?:\.\d{3})+(?:,\d{2})?|\d{2,6}(?:,\d{2})?)\s*(?:tl|₺)\b",
            text,
            flags=re.IGNORECASE,
        ):
            parsed = parse_try_price(match.group(0))
            if parsed is None:
                continue

            before = text[max(0, match.start() - 45):match.start()].casefold()
            after = text[match.end():min(len(text), match.end() + 25)].casefold()

            # Aylık/taksit/kredi/kupon tutarlarını satış fiyatı sanma.
            if any(
                term in before
                for term in (
                    "ayda", "taksit", "aylık", "aylik", "kredi",
                    "kupon", "kazanç", "kazanc", "tasarruf",
                )
            ):
                continue
            if any(
                term in after
                for term in ("taksit", "kupon", "kazanç", "kazanc", "tasarruf")
            ):
                continue

            context = text[
                max(0, match.start() - 90):
                min(len(text), match.end() + 90)
            ]
            context_folded = context.casefold()
            local_score = score
            local_score += 20 * sum(term in context_folded for term in POSITIVE_TERMS)
            candidates.append((local_score, parsed, context))

    strong = [row for row in candidates if row[0] >= 60]
    if not strong:
        return None

    strong.sort(key=lambda row: (-row[0], row[1]))
    best_score = strong[0][0]
    best_prices = [
        row[1]
        for row in strong
        if row[0] >= best_score - 10
    ]
    return min(best_prices) if best_prices else None
