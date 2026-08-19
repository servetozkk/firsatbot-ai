from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from app.services.normalization_service import normalize_text


@dataclass(slots=True)
class NormalizedOfferDetails:
    shipping_price: float | None = None
    shipping_method: str | None = None
    delivery_text: str | None = None
    warranty_type: str | None = None
    campaign_text: str | None = None
    installment_text: str | None = None
    currency: str = "TRY"
    is_sponsored: bool = False
    is_official_seller: bool = False


_FREE_SHIPPING_TERMS = (
    "ucretsiz kargo",
    "kargo bedava",
    "bedava kargo",
    "free shipping",
)

_SPONSORED_TERMS = (
    "sponsorlu",
    "reklam",
    "advertisement",
    "promoted",
)

_OFFICIAL_TERMS = (
    "resmi satici",
    "yetkili satici",
    "marka magazasi",
    "official store",
    "official seller",
)

_DELIVERY_PATTERNS = (
    r"(bugun\s+kargoda[^,.;|]*)",
    r"(yarin\s+kargoda[^,.;|]*)",
    r"(ayni\s+gun\s+kargo[^,.;|]*)",
    r"(\d+\s*[-–]\s*\d+\s*(?:is\s*)?gun(?:de)?[^,.;|]*)",
    r"(\d+\s*(?:is\s*)?gun(?:de)?\s+teslim[^,.;|]*)",
    r"(tahmini\s+teslim[^,.;|]*)",
)

# Bu desenler normalize_text() uygulanmış metinde çalışır.
_WARRANTY_PATTERNS = (
    r"((?:turkiye|distributor|ithalatci|resmi|uretici)\s+garantili)",
    r"(\d+\s*yil\s+(?:resmi\s+|uretici\s+)?garanti(?:li)?)",
    r"(garanti\s+suresi\s*:?\s*\d+\s*yil)",
    r"((?:apple|samsung|xiaomi|oppo|realme|huawei|honor|lenovo|asus|acer|hp|dell|msi)\s+turkiye\s+garantili)",
)

_INSTALLMENT_PATTERNS = (
    r"(\d+\s*taksit[^,.;|]*)",
    r"(pesin\s+fiyatina\s+\d+\s*taksit[^,.;|]*)",
)

_CAMPAIGN_PATTERNS = (
    r"(kupon[^,.;|]{0,90})",
    r"(sepette[^,.;|]{0,90})",
    r"(indirim[^,.;|]{0,90})",
    r"(kampanya[^,.;|]{0,90})",
)


def _clean(value: Any, max_length: int = 180) -> str | None:
    text = " ".join(str(value or "").split()).strip(" -|:;,")
    if not text:
        return None
    return text[:max_length]


def _parse_price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return max(float(value), 0.0)

    text = str(value).strip()
    if not text:
        return None

    normalized = normalize_text(text)
    if any(term in normalized for term in _FREE_SHIPPING_TERMS):
        return 0.0

    match = re.search(r"(\d[\d.\s]*[,.]?\d*)", text)
    if not match:
        return None

    raw = re.sub(r"\s+", "", match.group(1))
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    try:
        result = float(raw)
    except ValueError:
        return None
    return max(result, 0.0)


def _flatten_specifications(value: Any) -> str:
    if not value:
        return ""
    parsed = value
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (TypeError, json.JSONDecodeError):
            return parsed

    parts: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                parts.append(str(key))
                walk(nested)
        elif isinstance(item, (list, tuple, set)):
            for nested in item:
                walk(nested)
        elif item is not None:
            parts.append(str(item))

    walk(parsed)
    return " ".join(parts)


def _first_pattern(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _clean(match.group(1))
    return None


def _warranty_from_text(original_text: str) -> str | None:
    normalized_text = normalize_text(original_text)
    normalized_match = _first_pattern(normalized_text, _WARRANTY_PATTERNS)
    if not normalized_match:
        return None

    replacements = {
        "turkiye": "Türkiye",
        "distributor": "Distribütör",
        "ithalatci": "İthalatçı",
        "resmi": "Resmî",
        "uretici": "Üretici",
        "garantili": "garantili",
        "garanti": "garanti",
        "yil": "yıl",
    }
    words = normalized_match.split()
    restored = [replacements.get(word, word) for word in words]
    return " ".join(restored)


def normalize_offer_details(product: Any) -> NormalizedOfferDetails:
    name = str(getattr(product, "name", "") or "")
    description = str(getattr(product, "description", "") or "")
    specifications = _flatten_specifications(
        getattr(product, "specifications", None)
    )
    seller = str(getattr(product, "seller", "") or "")
    source_site = str(getattr(product, "source_site", "") or "")
    combined = " | ".join(
        part for part in (name, description, specifications, seller) if part
    )
    normalized = normalize_text(combined)

    shipping_price = _parse_price(getattr(product, "shipping_price", None))
    shipping_method = _clean(getattr(product, "shipping_method", None))
    delivery_text = _clean(getattr(product, "delivery_text", None))
    warranty_type = _clean(getattr(product, "warranty_type", None))
    campaign_text = _clean(getattr(product, "campaign_text", None))
    installment_text = _clean(getattr(product, "installment_text", None))
    currency = _clean(getattr(product, "currency", None), 8) or "TRY"

    if shipping_price is None and any(
        term in normalized for term in _FREE_SHIPPING_TERMS
    ):
        shipping_price = 0.0

    if not shipping_method:
        if shipping_price == 0:
            shipping_method = "Ücretsiz kargo"
        elif "magazadan teslim" in normalized:
            shipping_method = "Mağazadan teslim"
        elif "kargo" in normalized:
            shipping_method = "Kargo"

    if not delivery_text:
        delivery_text = _first_pattern(normalized, _DELIVERY_PATTERNS)

    if not warranty_type:
        warranty_type = _warranty_from_text(combined)

    if not installment_text:
        installment_text = _first_pattern(normalized, _INSTALLMENT_PATTERNS)

    if not campaign_text:
        campaign_text = _first_pattern(normalized, _CAMPAIGN_PATTERNS)

    explicit_sponsored = bool(getattr(product, "is_sponsored", False))
    is_sponsored = explicit_sponsored or any(
        term in normalized for term in _SPONSORED_TERMS
    )

    explicit_official = bool(getattr(product, "is_official_seller", False))
    normalized_seller = normalize_text(seller)
    normalized_source = normalize_text(source_site)
    seller_matches_store = bool(
        normalized_seller
        and normalized_source
        and (
            normalized_seller == normalized_source
            or normalized_source in normalized_seller
            or normalized_seller in normalized_source
        )
    )
    is_official_seller = (
        explicit_official
        or seller_matches_store
        or any(term in normalized for term in _OFFICIAL_TERMS)
    )

    return NormalizedOfferDetails(
        shipping_price=shipping_price,
        shipping_method=shipping_method,
        delivery_text=delivery_text,
        warranty_type=warranty_type,
        campaign_text=campaign_text,
        installment_text=installment_text,
        currency=currency.upper(),
        is_sponsored=is_sponsored,
        is_official_seller=is_official_seller,
    )


def apply_offer_details(offer: Any, details: NormalizedOfferDetails) -> None:
    values = {
        "shipping_price": details.shipping_price,
        "shipping_method": details.shipping_method,
        "delivery_text": details.delivery_text,
        "warranty_type": details.warranty_type,
        "campaign_text": details.campaign_text,
        "installment_text": details.installment_text,
        "currency": details.currency,
        "is_sponsored": details.is_sponsored,
        "is_official_seller": details.is_official_seller,
    }
    for field, value in values.items():
        if hasattr(offer, field):
            setattr(offer, field, value)
