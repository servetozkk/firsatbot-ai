from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from app.database.models import GlobalProduct, RawProduct


MODEL_CODE_PATTERN = re.compile(
    r"\b(?=[A-Z0-9._/-]{4,}\b)(?=[A-Z0-9._/-]*[A-Z])"
    r"(?=[A-Z0-9._/-]*\d)[A-Z0-9][A-Z0-9._/-]{3,}\b",
    re.I,
)


@dataclass(slots=True)
class MatchDecision:
    action: str
    confidence: float
    candidate_global_product_id: int | None
    reasons: list[str]
    conflicts: list[str]
    identifiers: dict[str, Any]


def _normalize(value: Any) -> str:
    text = str(value or "").casefold().translate(
        str.maketrans({"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c"})
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def extract_identifiers(raw: RawProduct, identity: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(v or "") for v in (
        raw.title_raw, raw.brand_raw, raw.model_raw,
        raw.specifications_raw, raw.description_raw, raw.store_product_id,
    ))
    codes = {
        value.strip("._/-").casefold()
        for value in MODEL_CODE_PATTERN.findall(text.upper())
        if not value.casefold().endswith(("gb","tb","mb"))
    }
    if identity.get("model_code"):
        codes.add(str(identity["model_code"]).casefold())
    return {
        "brand": _normalize(identity.get("normalized_brand")),
        "family": _normalize(identity.get("family")),
        "variant": _normalize(identity.get("variant")),
        "ram_gb": identity.get("ram_gb"),
        "storage_gb": identity.get("storage_gb"),
        "network": _normalize(identity.get("network")),
        "color": _normalize(identity.get("color")),
        "model_codes": sorted(codes),
    }


def _score(candidate: GlobalProduct, incoming: dict[str, Any]):
    score = 0.0
    reasons, conflicts = [], []
    brand = _normalize(candidate.normalized_brand)
    family = _normalize(candidate.family)
    variant = _normalize(candidate.variant)
    model_code = _normalize(candidate.model_code)

    if incoming["brand"] and incoming["brand"] == brand:
        score += 24; reasons.append("Marka eşleşti")
    elif incoming["brand"] and brand:
        score -= 60; conflicts.append("Marka farklı")

    ratio = SequenceMatcher(None, incoming["family"], family).ratio() if incoming["family"] and family else 0
    if ratio >= .98:
        score += 34; reasons.append("Ürün ailesi tam eşleşti")
    elif ratio >= .84:
        score += 22; reasons.append("Ürün ailesi yüksek benzerlikte")
    elif incoming["family"] and family:
        score -= 35; conflicts.append("Ürün ailesi farklı")

    if incoming["variant"] == variant:
        if variant:
            score += 14; reasons.append("Varyant eşleşti")
    elif incoming["variant"] or variant:
        score -= 45
        conflicts.append(f"Varyant farklı: {incoming['variant'] or 'standart'} / {variant or 'standart'}")

    for field, label, points in (("ram_gb","RAM",10),("storage_gb","Depolama",14)):
        a, b = incoming[field], getattr(candidate, field)
        if a is not None and b is not None:
            if int(a) == int(b):
                score += points; reasons.append(f"{label} eşleşti")
            else:
                score -= 50; conflicts.append(f"{label} farklı: {a} / {b}")

    codes = set(incoming["model_codes"])
    if model_code and model_code in codes:
        score += 55; reasons.append("Model kodu kesin eşleşti")
    elif model_code and codes:
        score -= 55; conflicts.append("Model kodu farklı")

    return max(0.0, min(100.0, score)), reasons, conflicts


def decide_global_match(*, db, raw: RawProduct, identity: dict[str, Any]) -> MatchDecision:
    identifiers = extract_identifiers(raw, identity)
    exact = db.query(GlobalProduct).filter(
        GlobalProduct.identity_key == str(identity.get("identity_key") or "")
    ).first()
    if exact:
        return MatchDecision("AUTO_MATCH",100.0,exact.id,["Identity key kesin eşleşti"],[],identifiers)

    query = db.query(GlobalProduct)
    if identifiers["brand"]:
        query = query.filter(GlobalProduct.normalized_brand == identifiers["brand"])
    scored = []
    for candidate in query.order_by(GlobalProduct.id.desc()).limit(250).all():
        score, reasons, conflicts = _score(candidate, identifiers)
        scored.append((score,candidate,reasons,conflicts))
    scored.sort(key=lambda x:x[0], reverse=True)

    if scored:
        score,candidate,reasons,conflicts = scored[0]
        hard = any(k in " ".join(conflicts) for k in ("Varyant","RAM","Depolama","Model kodu","Marka"))
        if score >= 90 and not hard:
            return MatchDecision("AUTO_MATCH",score,candidate.id,reasons,conflicts,identifiers)
        if score >= 55 or hard:
            return MatchDecision("REVIEW",score,candidate.id,reasons,conflicts,identifiers)

    completeness = sum(bool(v) for v in (
        identifiers["brand"], identifiers["family"],
        identifiers["model_codes"], identifiers["storage_gb"],
    ))
    if identifiers["brand"] and identifiers["family"]:
        return MatchDecision("CREATE_NEW",82.0 if completeness>=3 else 74.0,None,
                             ["Yeni ürün için yeterli kimlik alanı mevcut"],[],identifiers)
    return MatchDecision("REVIEW",35.0,None,
                         ["Kimlik bilgisi otomatik ürün oluşturmaya yetersiz"],[],identifiers)
