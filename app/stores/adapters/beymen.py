from __future__ import annotations

from app.stores.adapters.base import StoreAdapter

BEYMEN_ADAPTER = StoreAdapter(
    code="beymen",
    selectors=(
        "a[href*='/tr/p_']",
        "[data-product-url]",
        "[data-testid*='product'] a[href]",
        "[class*='product'] a[href]",
    ),
    excluded_path_tokens=("/arama", "/search", "/kategori/", "/marka/", "/kampanya/", "/sale-"),
    html_href_patterns=(
        r"[\"'](?P<url>https?://(?:www\.)?beymen\.com/tr/p_[^\"'<>\s]+_\d+(?:\?[^\"'<>\s]*)?)[\"']",
        r"[\"'](?P<url>/tr/p_[^\"'<>\s]+_\d+(?:\?[^\"'<>\s]*)?)[\"']",
        r"[\"'](?:productUrl|seoUrl|url)[\"']\s*:\s*[\"'](?P<url>/tr/p_[^\"']+_\d+[^\"']*)[\"']",
    ),
)
