from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Any

from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService


@dataclass(frozen=True, slots=True)
class MatchDecision:
    matched: bool
    score: float
    reason: str
    components: dict[str, float]
    gates: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fold(value: str | None) -> str:
    text = str(value or "").casefold().translate(
        str.maketrans(
            {
                "ı": "i",
                "ğ": "g",
                "ü": "u",
                "ş": "s",
                "ö": "o",
                "ç": "c",
            }
        )
    )
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def _tokens(value: str | None) -> set[str]:
    text = _fold(value)
    text = re.sub(r"(\d+)\s*(gb|tb|mb)", r"\1\2", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    noise = {
        "fiyat",
        "fiyati",
        "urun",
        "yeni",
        "orijinal",
        "garantili",
        "turkiye",
        "laptop",
        "notebook",
        "bilgisayar",
        "dizustu",
        "tasinabilir",
        "ram",
        "ssd",
        "fhd",
        "full",
        "hd",
        "inc",
        "inch",
    }
    return {
        token
        for token in text.split()
        if len(token) > 1 and token not in noise
    }


def _model_parts(product: Product) -> tuple[str, str]:
    identity = ProductIdentityService.parse(product)
    text = _fold(
        getattr(identity, "model_code", None)
        or product.model
        or product.name
    )

    match = re.search(
        r"\b([a-z]\d{3,5}[a-z]{1,3})(?:-([a-z0-9]{3,}))?\b",
        text,
    )
    if match:
        return match.group(1), match.group(2) or ""

    compact = re.sub(r"[^a-z0-9]+", "", text)
    return compact, ""


def _cpu_tokens(product: Product) -> set[str]:
    text = _fold(product.name)
    tokens: set[str] = set()

    for match in re.finditer(
        r"\b(?:core\s*)?(?:i[3579][-\s]*)?(\d{3,5}[a-z]{1,3})\b",
        text,
    ):
        tokens.add(match.group(1))

    for match in re.finditer(
        r"\bryzen\s*[3579]?\s*(\d{3,5}[a-z]{0,2})\b",
        text,
    ):
        tokens.add(match.group(1))

    return tokens


def _title_similarity(source: Product, candidate: Product) -> float:
    source_tokens = _tokens(source.name)
    candidate_tokens = _tokens(candidate.name)

    if not source_tokens or not candidate_tokens:
        return 0.0

    intersection = len(source_tokens & candidate_tokens)
    union = len(source_tokens | candidate_tokens)
    jaccard = intersection / max(1, union)

    source_text = " ".join(sorted(source_tokens))
    candidate_text = " ".join(sorted(candidate_tokens))
    sequence = SequenceMatcher(
        None,
        source_text,
        candidate_text,
    ).ratio()

    return round((jaccard * 0.7) + (sequence * 0.3), 4)


def _same_or_missing(
    source_value: int | float | None,
    candidate_value: int | float | None,
    *,
    tolerance: float = 0.0,
) -> tuple[bool, bool]:
    if source_value is None or candidate_value is None:
        return True, False

    return (
        abs(float(source_value) - float(candidate_value)) <= tolerance,
        True,
    )


def match_products_v15(
    *,
    source_product: Product,
    candidate_product: Product,
    minimum_score: float = 0.72,
) -> tuple[bool, float, str]:
    source = ProductIdentityService.parse(source_product)
    candidate = ProductIdentityService.parse(candidate_product)

    gates: list[str] = []
    components: dict[str, float] = {}

    source_brand = _fold(
        getattr(source, "brand", None)
        or source_product.brand
    )
    candidate_brand = _fold(
        getattr(candidate, "brand", None)
        or candidate_product.brand
    )

    if source_brand and candidate_brand and source_brand != candidate_brand:
        return False, 0.0, "V15 zorunlu kapı: marka farklı"

    if source_brand and candidate_brand:
        components["brand"] = 0.08
    else:
        components["brand"] = 0.03

    source_family, source_suffix = _model_parts(source_product)
    candidate_family, candidate_suffix = _model_parts(candidate_product)

    if (
        source_family
        and candidate_family
        and source_family != candidate_family
    ):
        return False, 0.0, "V15 zorunlu kapı: model ailesi farklı"

    if source_family and candidate_family:
        if (
            source_suffix
            and candidate_suffix
            and source_suffix != candidate_suffix
        ):
            return False, 0.0, "V15 zorunlu kapı: model varyantı farklı"

        if source_suffix and candidate_suffix == source_suffix:
            components["model"] = 0.46
            gates.append("tam model kodu")
        elif not candidate_suffix:
            components["model"] = 0.31
            gates.append("model ailesi aynı, aday son eki eksik")
        else:
            components["model"] = 0.25
            gates.append("model ailesi aynı")
    else:
        components["model"] = 0.0

    checks = (
        ("ram", source.ram_gb, candidate.ram_gb, 0.0, 0.12),
        (
            "storage",
            source.storage_gb,
            candidate.storage_gb,
            0.0,
            0.12,
        ),
        (
            "screen",
            source.screen_inch,
            candidate.screen_inch,
            0.25,
            0.05,
        ),
    )

    for name, source_value, candidate_value, tolerance, weight in checks:
        compatible, both_known = _same_or_missing(
            source_value,
            candidate_value,
            tolerance=tolerance,
        )

        if not compatible:
            return (
                False,
                0.0,
                f"V15 zorunlu kapı: {name} değeri farklı",
            )

        if both_known:
            components[name] = weight
            gates.append(f"{name} aynı")
        else:
            components[name] = weight * 0.25

    source_cpu = _cpu_tokens(source_product)
    candidate_cpu = _cpu_tokens(candidate_product)

    if source_cpu and candidate_cpu:
        if source_cpu.isdisjoint(candidate_cpu):
            return False, 0.0, "V15 zorunlu kapı: işlemci farklı"
        components["cpu"] = 0.12
        gates.append("işlemci aynı")
    else:
        components["cpu"] = 0.03

    title_similarity = _title_similarity(
        source_product,
        candidate_product,
    )
    components["title"] = min(0.15, title_similarity * 0.15)

    score = round(min(1.0, sum(components.values())), 4)

    # Tam model kodu varsa düşük başlık benzerliği engel değildir.
    exact_model = (
        source_family
        and source_family == candidate_family
        and source_suffix
        and source_suffix == candidate_suffix
    )

    # Son eki eksik aday yalnızca kritik donanım alanlarından en az ikisi
    # iki tarafta da biliniyor ve eşleşiyorsa kabul edilir.
    known_hardware_matches = sum(
        1
        for name in ("ram", "storage", "screen", "cpu")
        if components.get(name, 0.0) >= {
            "ram": 0.12,
            "storage": 0.12,
            "screen": 0.05,
            "cpu": 0.12,
        }[name]
    )

    family_fallback_safe = (
        source_family
        and source_family == candidate_family
        and not candidate_suffix
        and known_hardware_matches >= 2
        and title_similarity >= 0.32
    )

    matched = bool(
        (exact_model and score >= 0.62)
        or (family_fallback_safe and score >= minimum_score)
        or (
            not source_family
            and score >= 0.84
            and title_similarity >= 0.70
        )
    )

    reason = (
        "V15 eşleşti: "
        + ", ".join(gates)
        + f"; başlık={title_similarity:.3f}; toplam={score:.3f}"
        if matched
        else (
            "V15 eşik altında: "
            f"başlık={title_similarity:.3f}; "
            f"donanım={known_hardware_matches}; toplam={score:.3f}"
        )
    )

    return matched, score, reason
