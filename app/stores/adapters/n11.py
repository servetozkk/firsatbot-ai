from __future__ import annotations

from app.stores.adapters.base import StoreAdapter

N11_ADAPTER = StoreAdapter(
    code="n11",
    selectors=(
        "li.column",
        "li[data-product-id]",
        ".productItem",
        "[class*='product-card']",
        "a[href*='/urun/']",
    ),
    excluded_path_tokens=(
        "/arama", "/kategori/", "/magaza/", "/kampanyalar", "/hesabim",
    ),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?n11\.com/urun/[^"'<>\s]+)["']''',
        r'''["'](?P<url>/urun/[^"'<>\s]+)["']''',
        r'''["'](?:url|productUrl|seoUrl)["']\s*:\s*["'](?P<url>/urun/[^"']+)["']''',
    ),
)
