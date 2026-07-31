import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


TURKISH_TRANSLATION = str.maketrans(
    {
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u",
    }
)


def normalize_search_text(value: object) -> str:
    text = str(value or "").translate(TURKISH_TRANSLATION).casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def tokenize(value: object) -> list[str]:
    return [token for token in normalize_search_text(value).split() if token]


def parse_identity_attributes(identity_source: object) -> dict[str, str]:
    source = str(identity_source or "")
    attributes: dict[str, str] = {}
    for part in source.split("|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.split(":")[-1].strip().casefold()
        value = value.strip()
        if key and value:
            attributes[key] = value
    return attributes


def _token_score(token: str, fields: dict[str, str]) -> int:
    brand = fields.get("brand", "")
    model = fields.get("model", "")
    name = fields.get("name", "")
    category = fields.get("category", "")
    identity = fields.get("identity", "")

    if token == brand:
        return 42
    if token == model:
        return 40
    if token in brand.split():
        return 34
    if token in model.split():
        return 32
    if token in name.split():
        return 24
    if token in identity.split():
        return 20
    if token in category.split():
        return 12
    if token in name:
        return 8
    if token in identity:
        return 6
    return 0


def calculate_relevance(
    query: object,
    *,
    name: object,
    brand: object = "",
    model: object = "",
    category: object = "",
    identity_source: object = "",
) -> int:
    query_normalized = normalize_search_text(query)
    if not query_normalized:
        return 1

    fields = {
        "name": normalize_search_text(name),
        "brand": normalize_search_text(brand),
        "model": normalize_search_text(model),
        "category": normalize_search_text(category),
        "identity": normalize_search_text(identity_source),
    }
    haystack = " ".join(fields.values())
    tokens = tokenize(query_normalized)
    if not tokens or any(token not in haystack for token in tokens):
        return 0

    score = sum(_token_score(token, fields) for token in tokens)
    if query_normalized == fields["name"]:
        score += 120
    elif fields["name"].startswith(query_normalized):
        score += 70
    elif query_normalized in fields["name"]:
        score += 35

    if query_normalized == fields["model"]:
        score += 90
    elif fields["model"].startswith(query_normalized):
        score += 50

    return score


def matches_choice(value: object, selected: Iterable[str]) -> bool:
    selections = {normalize_search_text(item) for item in selected if str(item).strip()}
    if not selections:
        return True
    return normalize_search_text(value) in selections


def parse_capacity_gb(value: object) -> int | None:
    normalized = normalize_search_text(value).replace(" ", "")
    match = re.search(r"(\d+(?:\.\d+)?)(tb|gb)", normalized)
    if not match:
        return None
    amount = float(match.group(1))
    if match.group(2) == "tb":
        amount *= 1024
    return int(round(amount))
