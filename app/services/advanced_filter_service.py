from __future__ import annotations

from collections import Counter
from typing import Any

ENGINE_VERSION = "13.4.0"

# Akakçe tarzı kategoriye duyarlı filtre şeması. Veri yoksa filtre gösterilmez.
CATEGORY_FILTER_SCHEMA = {
    "laptop": ["processor", "cpu", "gpu", "graphics", "ram", "storage", "screen", "display", "panel", "refresh_rate", "operating_system"],
    "telefon": ["ram", "storage", "network", "nfc", "esim", "wireless_charging", "camera", "battery", "color"],
    "monitor": ["screen", "display", "panel", "refresh_rate", "resolution", "hdr", "color"],
    "televizyon": ["screen", "display", "panel", "refresh_rate", "resolution", "hdr", "smart_tv"],
    "tablet": ["ram", "storage", "network", "screen", "display", "battery", "color"],
}

FILTER_LABELS = {
    "processor": "İşlemci", "cpu": "İşlemci", "gpu": "Ekran kartı", "graphics": "Ekran kartı",
    "screen": "Ekran boyutu", "display": "Ekran türü", "panel": "Panel", "refresh_rate": "Yenileme hızı",
    "resolution": "Çözünürlük", "operating_system": "İşletim sistemi", "network": "Şebeke",
    "nfc": "NFC", "esim": "eSIM", "wireless_charging": "Kablosuz şarj", "camera": "Kamera",
    "battery": "Batarya", "color": "Renk", "hdr": "HDR", "smart_tv": "Smart TV",
}

ALIASES = {
    "notebook": "laptop", "dizustu": "laptop", "dizüstü": "laptop", "akilli telefon": "telefon",
    "akıllı telefon": "telefon", "tv": "televizyon", "monitör": "monitor",
}

def normalize_category(value: object) -> str:
    text = str(value or "").strip().casefold()
    for source, target in ALIASES.items():
        if source in text: return target
    for category in CATEGORY_FILTER_SCHEMA:
        if category in text: return category
    return text

def allowed_dynamic_keys(categories: list[str] | None = None) -> set[str]:
    if not categories:
        return set(FILTER_LABELS)
    keys:set[str]=set()
    for category in categories:
        keys.update(CATEGORY_FILTER_SCHEMA.get(normalize_category(category), FILTER_LABELS.keys()))
    return keys

def build_dynamic_facets(candidates: list[dict[str, Any]], selected_categories: list[str] | None = None, limit: int = 20) -> list[dict[str, Any]]:
    allowed=allowed_dynamic_keys(selected_categories)
    counters:dict[str,Counter]={}
    reserved={"ram","storage","brand","model","category"}
    for item in candidates:
        for key,value in (item.get("attributes") or {}).items():
            key=str(key).strip().casefold()
            if key in reserved or key not in allowed or key not in FILTER_LABELS or value in (None,""): continue
            counters.setdefault(key,Counter())[str(value).strip()] += 1
    facets=[]
    for key in sorted(counters, key=lambda k:(list(FILTER_LABELS).index(k),k)):
        items=[{"value":v,"label":v,"count":c} for v,c in counters[key].most_common(limit)]
        if items: facets.append({"key":key,"label":FILTER_LABELS[key],"items":items})
    return facets

def apply_dynamic_filters(candidates:list[dict[str,Any]], selected:dict[str,list[str]]) -> list[dict[str,Any]]:
    result=candidates
    for key,values in selected.items():
        wanted={str(v).strip().casefold() for v in values if str(v).strip()}
        if not wanted: continue
        result=[item for item in result if str((item.get("attributes") or {}).get(key,"")).strip().casefold() in wanted]
    return result

def filter_metadata(categories:list[str]|None=None)->dict[str,Any]:
    keys=allowed_dynamic_keys(categories)
    return {"engine_version":ENGINE_VERSION,"read_only":True,"categories":categories or [],"filters":[{"key":k,"label":FILTER_LABELS[k]} for k in FILTER_LABELS if k in keys]}
