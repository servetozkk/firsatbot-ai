from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from app.services.product_identity_service import ProductIdentityService


ACTIVE = "ACTIVE"
UPDATED = "UPDATED"
OUT_OF_STOCK = "OUT_OF_STOCK"
MISSING = "MISSING"
ARCHIVED = "ARCHIVED"


def normalize_seller(value: str | None) -> str:
    text = ProductIdentityService.normalize_token(value)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\b(ltd|sti|as|anonim sirketi|magazasi|store)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_offer_url(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    path = re.sub(r"/+", "/", parts.path or "/").rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def build_dedupe_key(*, store_id: int, store_product_id: str | None, seller: str | None, url: str | None) -> str:
    product_ref = str(store_product_id or "").strip().casefold()
    if not product_ref:
        product_ref = canonical_offer_url(url)
    payload = f"{int(store_id)}|{normalize_seller(seller)}|{product_ref}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def lifecycle_status(*, available: bool, active: bool, changed: bool = False, missing: bool = False) -> str:
    if not active:
        return ARCHIVED if missing else OUT_OF_STOCK
    if missing:
        return MISSING
    if not available:
        return OUT_OF_STOCK
    return UPDATED if changed else ACTIVE


@dataclass(frozen=True, slots=True)
class VariantCheck:
    compatible: bool
    score: float
    reasons: tuple[str, ...]


def validate_variant(incoming, candidate) -> VariantCheck:
    """Kesin varyant kapısı. Çelişki varsa puan ne olursa olsun eşleşmez."""
    reasons: list[str] = []
    if incoming.brand and candidate.brand and incoming.brand != candidate.brand:
        return VariantCheck(False, 0.0, ("marka çelişiyor",))
    if incoming.family and candidate.family and incoming.family != candidate.family:
        # Family benzerliği ana matching servisi tarafından ölçülür; burada yalnızca
        # açıkça farklı model ailelerini engelleriz.
        left = set(incoming.family.split())
        right = set(candidate.family.split())
        if not left.intersection(right):
            return VariantCheck(False, 0.0, ("model ailesi çelişiyor",))
    if incoming.variant != candidate.variant and (incoming.variant or candidate.variant):
        return VariantCheck(False, 0.0, ("Pro/Plus/Max/Ultra varyantı çelişiyor",))
    for label, left, right in (
        ("RAM", incoming.ram_gb, candidate.ram_gb),
        ("depolama", incoming.storage_gb, candidate.storage_gb),
    ):
        if left is not None and right is not None and left != right:
            return VariantCheck(False, 0.0, (f"{label} çelişiyor",))
    if incoming.network and candidate.network and incoming.network != candidate.network:
        return VariantCheck(False, 0.0, ("Wi-Fi/Cellular veya şebeke varyantı çelişiyor",))
    if incoming.model_code and candidate.model_code and incoming.model_code != candidate.model_code:
        return VariantCheck(False, 0.0, ("model kodu çelişiyor",))
    if incoming.product_code and candidate.product_code and incoming.product_code != candidate.product_code:
        reasons.append("ürün kodu farklı; diğer alanlar doğrulanacak")
    return VariantCheck(True, 100.0, tuple(reasons or ("kritik varyant alanları uyumlu",)))
