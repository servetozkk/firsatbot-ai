from __future__ import annotations
from typing import Any


def build_short_summary(group: Any, score: int, verdict_code: str, technical: dict) -> str:
    name = str(getattr(group, "name", "Bu ürün") or "Bu ürün")
    short = name[:78] + ("…" if len(name) > 78 else "")
    quality = "güçlü bir fırsat" if score >= 85 else "makul bir seçenek" if score >= 65 else "takip edilmesi gereken bir ürün"
    action = "şu an değerlendirilebilir" if verdict_code in {"buy", "consider"} else "alarm kurularak bir süre izlenebilir"
    highlight = technical.get("pros", [""])[0] if technical.get("pros") else "mevcut teknik özellikleri"
    return f"{short}, {highlight.lower()} ve fiyat konumuyla {quality}. Acil ihtiyacın varsa {action}."
