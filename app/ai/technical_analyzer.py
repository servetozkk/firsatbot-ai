from __future__ import annotations
import re
from typing import Any


def _text(group: Any, feature_headlines: list[dict] | None) -> str:
    parts = [str(getattr(group, "name", "") or ""), str(getattr(group, "description", "") or "")]
    for item in feature_headlines or []:
        parts.extend([str(item.get("label", "")), str(item.get("value", ""))])
    return " ".join(parts).lower()


def analyze_technical_profile(group: Any, feature_headlines: list[dict] | None) -> dict:
    text = _text(group, feature_headlines)
    pros, cons, tags = [], [], []
    def add_if(pattern: str, label: str, bucket: list[str]):
        if re.search(pattern, text, re.I) and label not in bucket: bucket.append(label)
    add_if(r"\b(16|24|32|64)\s*gb\b", "Güçlü bellek kapasitesi", pros)
    add_if(r"\b(1|2|4)\s*tb\b", "Geniş depolama alanı", pros)
    add_if(r"rtx\s*(4060|4070|4080|4090|5060|5070|5080|5090)", "Güçlü ekran kartı", pros)
    add_if(r"\b(120|144|165|180|200|240)\s*hz\b", "Akıcı yüksek yenileme hızı", pros)
    add_if(r"oled|mini\s*led|amoled", "Üst seviye ekran teknolojisi", pros)
    add_if(r"5g", "5G bağlantı desteği", pros)
    add_if(r"nfc", "NFC desteği", pros)
    add_if(r"\b(4|6)\s*gb\s*ram\b", "Bellek kapasitesi sınırlı", cons)
    add_if(r"\b(64|128)\s*gb\b", "Depolama alanı sınırlı olabilir", cons)
    add_if(r"freedos|dos\b", "İşletim sistemi kurulumu gerekebilir", cons)
    add_if(r"celeron|n4020|n4500", "Temel seviye işlemci", cons)
    if re.search(r"rtx|gaming|oyun", text): tags += ["Oyuncular", "İçerik üreticileri"]
    if re.search(r"ryzen\s*[579]|core\s*(i[579]|ultra)|m[1-9]", text): tags += ["Yazılımcılar", "Yoğun çoklu görev"]
    if re.search(r"hafif|ultrabook|air|slim", text): tags += ["Öğrenciler", "Sık seyahat edenler"]
    if re.search(r"iphone|galaxy|xiaomi|telefon|smartphone", text): tags += ["Günlük kullanım", "Mobil fotoğrafçılık"]
    if not tags: tags = ["Günlük kullanım", "Fiyat odaklı kullanıcılar"]
    return {"pros": pros[:5], "cons": cons[:4], "suitability": list(dict.fromkeys(tags))[:4]}
