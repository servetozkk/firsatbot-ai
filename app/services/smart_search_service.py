from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from typing import Any, Iterable

CATEGORY_ALIASES = {
    "laptop": ("laptop", "notebook", "dizustu", "dizüstü", "oyuncu bilgisayari", "oyuncu bilgisayarı"),
    "telefon": ("telefon", "cep telefonu", "akilli telefon", "akıllı telefon", "iphone", "android"),
    "monitor": ("monitor", "monitör", "ekran"),
    "tablet": ("tablet", "ipad"),
    "televizyon": ("televizyon", "tv"),
    "kulaklik": ("kulaklik", "kulaklık", "headset"),
}

PURPOSE_ALIASES = {
    "gaming": ("oyun", "oyuncu", "gaming", "fps"),
    "student": ("ogrenci", "öğrenci", "okul", "ders"),
    "business": ("is bilgisayari", "iş bilgisayarı", "ofis", "business"),
    "best_value": ("fiyat performans", "fiyat/performans", "en mantikli", "en mantıklı", "best value"),
}

SYNONYMS = {
    "oyuncu bilgisayari": "gaming laptop",
    "oyuncu bilgisayarı": "gaming laptop",
    "cep telefonu": "telefon",
    "akilli telefon": "telefon",
    "akıllı telefon": "telefon",
    "dizustu": "laptop",
    "dizüstü": "laptop",
    "is bilgisayari": "business laptop",
    "iş bilgisayarı": "business laptop",
}

COMMON_CORRECTIONS = {
    "samsng": "samsung", "ıphone": "iphone", "iphne": "iphone",
    "lenovo log": "lenovo loq", "lenovo loq": "lenovo loq", "asus tufg": "asus tuf",
    "monıtor": "monitor", "monitpr": "monitor", "lapotp": "laptop", "laptp": "laptop",
}

BRAND_ALIASES = {
    "apple": ("apple", "iphone", "macbook", "ipad"),
    "samsung": ("samsung", "galaxy"),
    "lenovo": ("lenovo", "loq", "legion", "thinkpad", "ideapad"),
    "asus": ("asus", "rog", "tuf", "zenbook", "vivobook"),
    "hp": ("hp", "victus", "omen", "pavilion"),
    "acer": ("acer", "nitro", "predator", "aspire"),
    "xiaomi": ("xiaomi", "redmi", "poco"),
}


def normalize_text(value: object) -> str:
    raw = unicodedata.normalize("NFKD", str(value or "").casefold())
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = raw.replace("ı", "i")
    return " ".join(re.sub(r"[^a-z0-9+./]+", " ", raw).split())


def _canonical_query(query: str) -> tuple[str, list[str]]:
    q = normalize_text(query)
    corrections: list[str] = []
    for wrong, right in COMMON_CORRECTIONS.items():
        if normalize_text(wrong) in q:
            q = q.replace(normalize_text(wrong), normalize_text(right))
            corrections.append(f"{wrong} → {right}")
    for source, target in SYNONYMS.items():
        src = normalize_text(source)
        if src in q:
            q = q.replace(src, normalize_text(target))
    return q, corrections


def _price_value(number: str, unit: str | None) -> float:
    value = float(number.replace(",", "."))
    if unit in {"bin", "k"}:
        value *= 1000
    return value


def _find_category(q: str) -> str | None:
    for canonical, aliases in CATEGORY_ALIASES.items():
        if any(normalize_text(alias) in q for alias in aliases):
            return canonical
    return None


def _find_brand(q: str) -> str | None:
    for canonical, aliases in BRAND_ALIASES.items():
        if any(re.search(rf"\b{re.escape(normalize_text(alias))}\b", q) for alias in aliases):
            return canonical
    return None


def _find_purpose(q: str) -> str | None:
    for canonical, aliases in PURPOSE_ALIASES.items():
        if any(normalize_text(alias) in q for alias in aliases):
            return canonical
    return None


def _capacity_gb(value: str, unit: str) -> int:
    number = float(value.replace(",", "."))
    return int(round(number * 1024)) if unit.lower() == "tb" else int(round(number))


@dataclass
class SmartQuery:
    raw_query: str
    normalized_query: str
    search_text: str
    category: str | None = None
    brand: str | None = None
    purpose: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    ram_gb: int | None = None
    storage_gb: int | None = None
    gpu: str | None = None
    display: str | None = None
    refresh_rate_hz: int | None = None
    network: str | None = None
    intent: str = "search"
    corrections: list[str] | None = None
    extracted: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_smart_query(query: str) -> dict[str, Any]:
    q, corrections = _canonical_query(query)
    extracted: list[str] = []
    category = _find_category(q)
    brand = _find_brand(q)
    purpose = _find_purpose(q)
    if category: extracted.append(f"Kategori: {category}")
    if brand: extracted.append(f"Marka: {brand}")
    if purpose: extracted.append(f"Amaç: {purpose}")

    price_min = price_max = None
    price_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(bin|k)?\s*(?:tl|₺)?\s*(alti|altinda|altı|altında|kadar)", q)
    if price_match:
        price_max = _price_value(price_match.group(1), price_match.group(2))
        extracted.append(f"En fazla: {int(price_max):,} TL".replace(",", "."))
    price_min_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(bin|k)?\s*(?:tl|₺)?\s*(ustu|ustunde|üstü|üstünde|uzeri|üzeri)", q)
    if price_min_match:
        price_min = _price_value(price_min_match.group(1), price_min_match.group(2))
        extracted.append(f"En az: {int(price_min):,} TL".replace(",", "."))

    ram_gb = None
    ram = re.search(r"\b(4|6|8|12|16|24|32|48|64|96|128)\s*(?:gb|g)?\s*ram\b|\bram\s*(4|6|8|12|16|24|32|48|64|96|128)\b", q)
    if ram:
        ram_gb = int(ram.group(1) or ram.group(2)); extracted.append(f"RAM: {ram_gb} GB")

    storage_gb = None
    storage = re.search(r"\b(128|256|480|512|1000|1024|2000|2048|4000|4096|1|2|4)\s*(tb|gb)\s*(?:ssd|nvme|depolama|disk)?\b", q)
    if storage:
        storage_gb = _capacity_gb(storage.group(1), storage.group(2)); extracted.append(f"Depolama: {storage_gb} GB")

    gpu = None
    gpu_match = re.search(r"\b(rtx\s*\d{4}(?:\s*ti|\s*super)?|gtx\s*\d{3,4}(?:\s*ti)?|rx\s*\d{4}(?:\s*xt)?)\b", q)
    if gpu_match:
        gpu = re.sub(r"\s+", " ", gpu_match.group(1)).upper(); extracted.append(f"GPU: {gpu}")

    display = next((item.upper() for item in ("oled", "amoled", "ips", "mini led") if item in q), None)
    if display: extracted.append(f"Ekran: {display}")
    hz = re.search(r"\b(60|75|90|120|144|165|180|240|300|360)\s*hz\b", q)
    refresh = int(hz.group(1)) if hz else None
    if refresh: extracted.append(f"Yenileme: {refresh} Hz")
    network = "5g" if re.search(r"\b5g\b", q) else "4g" if re.search(r"\b4g\b", q) else None
    if network: extracted.append(f"Şebeke: {network.upper()}")

    intent = "best_value" if purpose == "best_value" else "gaming" if purpose == "gaming" else "search"

    removable = list(extracted)
    search_tokens = q
    for phrase in ("alti", "altinda", "altı", "altında", "kadar", "ustu", "ustunde", "üzeri", "en iyi", "fiyat performans"):
        search_tokens = search_tokens.replace(normalize_text(phrase), " ")
    search_text = " ".join(search_tokens.split())

    return SmartQuery(
        raw_query=query, normalized_query=q, search_text=search_text or q,
        category=category, brand=brand, purpose=purpose, price_min=price_min, price_max=price_max,
        ram_gb=ram_gb, storage_gb=storage_gb, gpu=gpu, display=display,
        refresh_rate_hz=refresh, network=network, intent=intent,
        corrections=corrections, extracted=extracted,
    ).to_dict()


def _contains(item: dict[str, Any], needle: str) -> bool:
    hay = normalize_text(" ".join(str(item.get(k, "")) for k in ("name", "brand", "model", "category", "ram", "storage")))
    hay += " " + normalize_text(" ".join(f"{k} {v}" for k, v in (item.get("attributes") or {}).items()))
    wanted = normalize_text(needle)
    if wanted in hay:
        return True
    # GPU/model kodları mağaza başlıklarında RTX5060 veya RTX 5060 gibi
    # boşluklu/boşluksuz yazılabilir. Alfasayısal kompakt karşılaştırma bu
    # biçimleri eşdeğer kabul eder; normal kelime eşleşmesini gevşetmez.
    compact_hay = re.sub(r"[^a-z0-9]+", "", hay)
    compact_wanted = re.sub(r"[^a-z0-9]+", "", wanted)
    return bool(compact_wanted and compact_wanted in compact_hay)


def _capacity_from_item(item: dict[str, Any], key: str) -> int | None:
    match = re.search(r"(\d+)", str(item.get(key, "")))
    return int(match.group(1)) if match else None


def enrich_and_rank_candidates(candidates: Iterable[dict[str, Any]], parsed: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for original in candidates:
        item = dict(original)
        reasons: list[str] = []
        score = float(item.get("relevance", 0) or 0)
        hard_fail = False
        category = parsed.get("category")
        if category:
            category_match = category in normalize_text(item.get("category")) or category in normalize_text(item.get("name"))
            if category_match: score += 28; reasons.append("Kategori eşleşiyor")
            else: hard_fail = True
        brand = parsed.get("brand")
        if brand:
            if brand in normalize_text(item.get("brand")) or brand in normalize_text(item.get("name")):
                score += 22; reasons.append(f"{brand.title()} marka eşleşmesi")
            else: score -= 12
        price = float(item.get("price", 0) or 0)
        if parsed.get("price_min") is not None and price < float(parsed["price_min"]): hard_fail = True
        if parsed.get("price_max") is not None and price > float(parsed["price_max"]): hard_fail = True
        if parsed.get("price_min") is not None or parsed.get("price_max") is not None: reasons.append("Bütçe aralığına uygun")
        ram = parsed.get("ram_gb")
        if ram:
            current = _capacity_from_item(item, "ram")
            if current == ram:
                score += 24; reasons.append(f"{ram} GB RAM")
            else:
                hard_fail = True
        storage = parsed.get("storage_gb")
        if storage:
            current = _capacity_from_item(item, "storage")
            if current == storage:
                score += 24; reasons.append(f"{storage} GB depolama")
            else:
                hard_fail = True
        gpu = parsed.get("gpu")
        if gpu:
            if _contains(item, gpu): score += 32; reasons.append(f"{gpu} içeriyor")
            else: hard_fail = True
        display = parsed.get("display")
        if display:
            if _contains(item, display): score += 18; reasons.append(f"{display} ekran")
            else: hard_fail = True
        hz = parsed.get("refresh_rate_hz")
        if hz:
            if _contains(item, f"{hz} hz") or _contains(item, f"{hz}hz"): score += 16; reasons.append(f"{hz} Hz")
            else: score -= 6
        network = parsed.get("network")
        if network:
            if _contains(item, network): score += 20; reasons.append(f"{network.upper()} şebeke")
            else: hard_fail = True
        purpose = parsed.get("purpose")
        if purpose == "gaming" and any(_contains(item, token) for token in ("rtx", "gtx", "rx", "gaming", "oyuncu")):
            score += 14; reasons.append("Oyun kullanımına uygun")
        if purpose == "student" and category in {"laptop", "tablet"}: score += 8; reasons.append("Öğrenci kullanımına uygun")
        if purpose == "best_value":
            offer_count = int(item.get("offer_count", 0) or 0)
            score += min(12, offer_count * 3); reasons.append("Fiyat/performans sıralaması")
        if hard_fail: continue
        item["semantic_score"] = max(0, min(100, int(round(score))))
        item["search_reasons"] = reasons[:5] or ["Metin eşleşmesi"]
        item["relevance"] = score
        result.append(item)
    result.sort(key=lambda x: (-float(x.get("relevance", 0)), -int(x.get("offer_count", 0)), float(x.get("price", 0))))
    return result


def build_autocomplete(query: str, products: Iterable[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    parsed = parse_smart_query(query)
    q = parsed["normalized_query"]
    suggestions: list[tuple[float, dict[str, Any]]] = []
    templates = []
    if parsed.get("category"):
        templates += [f"{parsed['category']} fiyat performans", f"30 bin altı {parsed['category']}"]
    if parsed.get("gpu"):
        templates += [f"{parsed['gpu']} laptop", f"{parsed['gpu']} fiyat performans laptop"]
    for text in templates:
        suggestions.append((2.0, {"type": "query", "name": text, "url": f"/arama?q={text.replace(' ', '+')}", "icon": "✨"}))
    for item in products:
        name = str(item.get("name", ""))
        norm = normalize_text(name)
        ratio = SequenceMatcher(None, q, norm).ratio()
        if q in norm: ratio += .6
        if ratio >= .45:
            suggestions.append((ratio, {"type": "product", "name": name, "url": item.get("url"), "icon": "🔎", "price": item.get("price")}))
    seen=set(); out=[]
    for _, row in sorted(suggestions, key=lambda x: -x[0]):
        key=(row["type"], row["name"])
        if key in seen: continue
        seen.add(key); out.append(row)
        if len(out)>=limit: break
    return out
