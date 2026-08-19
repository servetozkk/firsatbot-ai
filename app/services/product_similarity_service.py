from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable

STOP_WORDS = {
    "ve", "ile", "icin", "için", "gb", "tb", "ram", "ssd", "nvme",
    "urun", "ürün", "model", "yeni", "garantili", "turkiye", "türkiye",
    "renk", "siyah", "beyaz", "mavi", "gri", "gumus", "gümüş", "gold",
}

FEATURE_ALIASES = {
    "ram": {"ram", "ram_sistem_bellegi", "bellek", "sistem_bellegi"},
    "storage": {"depolama_kapasitesi", "depolama", "ssd_kapasitesi", "hard_disk_kapasitesi"},
    "cpu": {"islemci_modeli", "islemci_tipi", "islemci", "cpu"},
    "gpu": {"ekran_kart", "ekran_karti", "ekran_kart_tipi", "gpu"},
    "screen": {"ekran_boyutu", "ekran", "screen_size"},
    "network": {"5g", "sebeke", "network", "baglanti_tipi"},
    "refresh": {"yenileme_h_z", "ekran_yenileme_h_z", "refresh_rate"},
}

WEIGHTS = {
    "lexical": 25.0,
    "brand": 7.0,
    "model": 8.0,
    "ram": 9.0,
    "storage": 9.0,
    "cpu": 10.0,
    "gpu": 12.0,
    "screen": 5.0,
    "network": 5.0,
    "refresh": 3.0,
    "price": 7.0,
}


@dataclass(frozen=True)
class SimilarityProfile:
    group_id: int
    identity_key: str
    name: str
    brand: str | None
    model: str | None
    category: str | None
    image: str | None
    features: dict[str, Any]
    best_price: float = 0.0


def _norm(value: Any) -> str:
    text = str(value or "").casefold()
    text = text.translate(str.maketrans("çğıöşü", "cgiosu"))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _tokens(value: Any) -> set[str]:
    return {part for part in _norm(value).split() if len(part) > 1 and part not in STOP_WORDS}


def category_family(value: str | None) -> str:
    text = _norm(value)
    rules = (
        ("phone", ("telefon", "iphone", "android", "cep telefonu")),
        ("laptop", ("laptop", "notebook", "dizustu")),
        ("desktop", ("masaustu", "oyuncu bilgisayari", "hazir sistem")),
        ("monitor", ("monitor", "ekran")),
        ("bag", ("canta", "kilif", "koruyucu")),
        ("stand", ("stand", "sehpa")),
        ("fitness", ("kosu bandi", "fitness", "kondisyon")),
    )
    for family, terms in rules:
        if any(term in text for term in terms):
            return family
    tokens = [token for token in text.split() if token not in {"elektronik", "urun", "aksesuar"}]
    return " ".join(tokens[-3:]) if tokens else "unknown"


def _feature_value(features: dict[str, Any], logical_name: str) -> Any:
    aliases = FEATURE_ALIASES.get(logical_name, {logical_name})
    normalized = {_norm(key).replace(" ", "_"): value for key, value in features.items()}
    for alias in aliases:
        key = _norm(alias).replace(" ", "_")
        if key in normalized and normalized[key] not in (None, ""):
            return normalized[key]
    return None


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        match = re.search(r"\d+(?:[.,]\d+)?", str(value))
        return float(match.group(0).replace(",", ".")) if match else None


def _text_similarity(left: Any, right: Any) -> float | None:
    if left in (None, "") or right in (None, ""):
        return None
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 1.0 if _norm(left) == _norm(right) else 0.0
    return len(a & b) / len(a | b)


def _numeric_similarity(left: Any, right: Any, tolerance: float = 0.25) -> float | None:
    a, b = _number(left), _number(right)
    if a is None or b is None:
        return None
    if a == b:
        return 1.0
    maximum = max(abs(a), abs(b), 1.0)
    relative = abs(a - b) / maximum
    return max(0.0, 1.0 - relative / max(tolerance, 0.01))


def _boolean_similarity(left: Any, right: Any) -> float | None:
    if left in (None, "") or right in (None, ""):
        return None
    def convert(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return _norm(value) in {"1", "true", "evet", "var", "5g"}
    return 1.0 if convert(left) == convert(right) else 0.0


def score_similarity_profiles(current: SimilarityProfile, candidate: SimilarityProfile) -> dict[str, Any]:
    if current.group_id == candidate.group_id:
        return {"score": 0.0, "compatible": False, "reasons": ["Aynı ürün grubu"]}

    current_family = category_family(current.category)
    candidate_family = category_family(candidate.category)
    if current_family != candidate_family:
        return {
            "score": 0.0,
            "compatible": False,
            "category_family": candidate_family,
            "reasons": ["Farklı ürün kategorisi"],
            "components": {},
        }

    components: dict[str, float] = {}
    available_weight = 0.0
    weighted_score = 0.0

    lexical = _text_similarity(
        f"{current.brand} {current.model} {current.name}",
        f"{candidate.brand} {candidate.model} {candidate.name}",
    ) or 0.0
    components["lexical"] = lexical

    brand = 1.0 if _norm(current.brand) and _norm(current.brand) == _norm(candidate.brand) else 0.0
    model = _text_similarity(current.model, candidate.model)
    components["brand"] = brand
    components["model"] = model if model is not None else lexical

    comparators = {
        "ram": lambda a, b: _numeric_similarity(a, b, tolerance=0.50),
        "storage": lambda a, b: _numeric_similarity(a, b, tolerance=0.60),
        "cpu": _text_similarity,
        "gpu": _text_similarity,
        "screen": lambda a, b: _numeric_similarity(a, b, tolerance=0.25),
        "network": _boolean_similarity,
        "refresh": lambda a, b: _numeric_similarity(a, b, tolerance=0.50),
    }
    for name, comparator in comparators.items():
        value = comparator(_feature_value(current.features, name), _feature_value(candidate.features, name))
        if value is not None:
            components[name] = max(0.0, min(1.0, float(value)))

    if current.best_price > 0 and candidate.best_price > 0:
        ratio = candidate.best_price / current.best_price
        components["price"] = max(0.0, 1.0 - abs(math.log(max(ratio, 0.01))) / math.log(2.5))

    for name, value in components.items():
        weight = WEIGHTS[name]
        available_weight += weight
        weighted_score += value * weight

    score = weighted_score / available_weight * 100 if available_weight else 0.0

    # Kritik varyant farklarında puanı güvenli biçimde sınırla.
    for critical in ("network", "gpu"):
        if critical in components and components[critical] == 0.0:
            score = min(score, 64.0)
    for critical in ("ram", "storage"):
        if critical in components and components[critical] < 0.25:
            score = min(score, 69.0)

    reasons: list[str] = []
    if components.get("gpu", 0) >= 0.8:
        reasons.append("Aynı veya çok yakın ekran kartı")
    if components.get("cpu", 0) >= 0.65:
        reasons.append("Benzer işlemci sınıfı")
    if components.get("ram", 0) >= 0.9 and components.get("storage", 0) >= 0.9:
        reasons.append("RAM ve depolama kapasitesi eşleşiyor")
    elif components.get("ram", 0) >= 0.9:
        reasons.append("Aynı RAM kapasitesi")
    elif components.get("storage", 0) >= 0.9:
        reasons.append("Aynı depolama kapasitesi")
    if components.get("network", 0) >= 1.0:
        reasons.append("Aynı şebeke varyantı")
    if components.get("price", 0) >= 0.75:
        reasons.append("Yakın fiyat segmenti")
    if brand:
        reasons.append("Aynı marka")
    if not reasons:
        reasons.append(f"Teknik ve isim benzerliği %{score:.0f}")

    return {
        "score": round(max(0.0, min(100.0, score)), 1),
        "compatible": score >= 35.0,
        "category_family": current_family,
        "reasons": reasons[:3],
        "components": {key: round(value * 100, 1) for key, value in components.items()},
        "feature_coverage": round(available_weight / sum(WEIGHTS.values()) * 100, 1),
    }


def load_feature_maps(db, group_ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    from app.database.models import ProductFeature, ProductFeatureValue

    ids = list({int(value) for value in group_ids})
    if not ids:
        return {}
    rows = (
        db.query(ProductFeatureValue, ProductFeature)
        .join(ProductFeature, ProductFeature.id == ProductFeatureValue.feature_id)
        .filter(ProductFeatureValue.product_group_id.in_(ids))
        .all()
    )
    result: dict[int, dict[str, Any]] = {group_id: {} for group_id in ids}
    for value_row, feature in rows:
        value = value_row.value_number
        if value is None:
            value = value_row.value_boolean
        if value is None:
            value = value_row.value_text
        result.setdefault(value_row.product_group_id, {})[feature.code] = value
    return result
