from __future__ import annotations

from app.stores.adapters.base import StoreAdapter

IDEFIX_ADAPTER = StoreAdapter(
    code="idefix",
    selectors=(
        "a[href*='-p-']",
        "a[href*='/urun/']",
        "[data-testid*='product'] a[href]",
        "[data-product-url]",
        "[class*='product'] a[href]",
    ),
    excluded_path_tokens=("/ara", "/kategori/", "/marka/", "/kampanya/", "/hesabim"),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?idefix\.com/[^"'<>\s]+-p-\d+(?:\?[^"'<>\s]*)?)["']''',
        r'''["'](?P<url>/[^"'<>\s]+-p-\d+(?:\?[^"'<>\s]*)?)["']''',
        r'''["'](?P<url>https?://(?:www\.)?idefix\.com/urun/[^"'<>\s]+)["']''',
        r'''["'](?P<url>/urun/[^"'<>\s]+)["']''',
        r'''["'](?:productUrl|seoUrl|url)["']\s*:\s*["'](?P<url>/urun/[^"']+)["']''',
    ),
)
