from __future__ import annotations

import re

from app.stores.adapters.base import StoreAdapter


class TeknosaAdapter(StoreAdapter):
    def normalize_label(self, label: str) -> str:
        text = super().normalize_label(label)
        text = re.sub(r"(?i)(x\d{3,5}[a-z]{1,3})a\d{1,3}\b", r"\1", text)
        text = re.sub(r"(?i)([a-z]{1,4}\d{3,6})a\d{1,3}\b", r"\1", text)
        return text


TEKNOSA_ADAPTER = TeknosaAdapter(
    code="teknosa",
    selectors=(
        "li.product-item",
        "div.product-item",
        "[class*='product-item']",
        "[class*='product-card']",
        "[data-product-code]",
        "a[href*='-p-']",
        "a[href*='/urun/']",
    ),
    excluded_path_tokens=(
        "/arama/", "/kampanya", "/marka/", "/kategori/", "/magaza/",
    ),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?teknosa\.com/[^"'<>\s]+-p-\d+[^"'<>\s]*)["']''',
        r'''["'](?P<url>/[^"'<>\s]+-p-\d+[^"'<>\s]*)["']''',
        r'''["'](?:url|productUrl|productURL|pdpUrl)["']\s*:\s*["'](?P<url>/[^"']+)["']''',
    ),
)
