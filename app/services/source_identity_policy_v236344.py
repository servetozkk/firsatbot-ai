from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

_OPAQUE_URL_STORES = {"amazon", "demo", "unknown"}
_STOP = {
    "ve", "ile", "icin", "uyumlu", "fiyati", "fiyatlari", "ozellikleri",
    "urun", "akilli", "telefon", "laptop", "bilgisayar", "tablet",
    "beyaz", "siyah", "gri", "gb", "ram", "ssd", "turkiye", "garantili",
}
_PRODUCT_CLASSES = {
    "PHONE": ("iphone", "galaxy a", "redmi note", "cep telefonu"),
    "HEADPHONE": ("freebuds", "kulaklik", "earbuds", "airpods"),
    "POWERBANK": ("powerbank", "mah tasinabilir", "hizli sarj cihazi"),
    "CASE": ("kilif", "koruyucu kapak", "telefon kilifi"),
    "DETERGENT": ("deterjan", "camasir deterjani"),
}
_GPU_RE = re.compile(r"\brtx\s*([2345]\d{3})\b", re.I)
_SERIES_RE = re.compile(r"\b([a-z]{1,3})(\d{2,3})\b", re.I)


@dataclass(frozen=True)
class SourceIdentityVerdict:
    quarantine: bool
    reasons: tuple[str, ...]

    @property
    def reason_text(self) -> str:
        return " | ".join(self.reasons)


def _fold(value) -> str:
    value = unquote(str(value or ""))
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.casefold().translate(str.maketrans({
        "ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
    }))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _tokens(value) -> set[str]:
    return {token for token in _fold(value).split() if len(token) >= 3 and token not in _STOP and not token.isdigit()}


def _detect_classes(value) -> set[str]:
    text = _fold(value)
    return {cls for cls, markers in _PRODUCT_CLASSES.items() if any(marker in text for marker in markers)}


def _payload(identity_payload) -> dict:
    if isinstance(identity_payload, dict):
        return identity_payload
    try:
        data = json.loads(identity_payload or "{}")
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _is_opaque_url(*, store_code: str, source_url: str) -> bool:
    store = _fold(store_code).replace(" ", "")
    if store in _OPAQUE_URL_STORES:
        return True
    parsed = urlparse(str(source_url or ""))
    return bool(re.fullmatch(r"/dp/[A-Z0-9]+/?", parsed.path or "", re.I))


def _url_class_conflict(*, store_code: str, source_url: str, raw_title: str) -> bool:
    if _is_opaque_url(store_code=store_code, source_url=source_url):
        return False
    parsed = urlparse(str(source_url or ""))
    title_classes = _detect_classes(raw_title)
    url_classes = _detect_classes(parsed.path)
    return bool(title_classes and url_classes and title_classes.isdisjoint(url_classes))


def _gpu_conflict(raw_title: str, canonical_name: str) -> bool:
    raw_gpu = {m.group(1) for m in _GPU_RE.finditer(_fold(raw_title))}
    canonical_gpu = {m.group(1) for m in _GPU_RE.finditer(_fold(canonical_name))}
    return bool(raw_gpu and canonical_gpu and raw_gpu.isdisjoint(canonical_gpu))


def _series_conflict(raw_title: str, canonical_name: str) -> bool:
    ignored = {"rtx", "gb", "tb", "hz", "mp", "mah", "ip"}

    def collect(text: str) -> dict[str, set[str]]:
        result: dict[str, set[str]] = {}
        for prefix, number in _SERIES_RE.findall(_fold(text)):
            prefix = prefix.casefold()
            if prefix in ignored:
                continue
            result.setdefault(prefix, set()).add(number)
        return result

    left, right = collect(raw_title), collect(canonical_name)
    return any(left[prefix].isdisjoint(right[prefix]) for prefix in left.keys() & right.keys() if left[prefix] and right[prefix])


def _very_low_overlap(raw_title: str, canonical_name: str) -> bool:
    left, right = _tokens(raw_title), _tokens(canonical_name)
    if len(left) < 3 or len(right) < 3:
        return False
    union = left | right
    return bool(union and (len(left & right) / len(union)) < 0.12)


def evaluate_source_identity_values_v236344(*, store_code: str, source_url: str, raw_title: str, identity_payload, canonical_name: str) -> SourceIdentityVerdict:
    reasons: list[str] = []
    if _url_class_conflict(store_code=store_code, source_url=source_url, raw_title=raw_title):
        reasons.append("SEMANTIC_URL_PRODUCT_CLASS_CONFLICT")

    payload = _payload(identity_payload)
    if bool(payload.get("canonical_override")):
        if _gpu_conflict(raw_title, canonical_name):
            reasons.append("CANONICAL_OVERRIDE_GPU_CONFLICT")
        if _series_conflict(raw_title, canonical_name):
            reasons.append("CANONICAL_OVERRIDE_SERIES_CONFLICT")
        if _very_low_overlap(raw_title, canonical_name):
            reasons.append("CANONICAL_OVERRIDE_VERY_LOW_TITLE_OVERLAP")

    quarantine = any(reason in reasons for reason in (
        "SEMANTIC_URL_PRODUCT_CLASS_CONFLICT",
        "CANONICAL_OVERRIDE_GPU_CONFLICT",
        "CANONICAL_OVERRIDE_SERIES_CONFLICT",
    ))
    return SourceIdentityVerdict(quarantine, tuple(reasons))
