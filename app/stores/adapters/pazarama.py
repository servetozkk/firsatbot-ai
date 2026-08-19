from __future__ import annotations

from app.stores.adapters.base import StoreAdapter

PAZARAMA_ADAPTER = StoreAdapter(
    code="pazarama",
    selectors=(
        "a[href*='-p-']",
        "a[href*='/urun/']",
        "[data-product-url]",
        "[data-testid*='product'] a[href]",
    ),
    excluded_path_tokens=("/arama", "/kategori/", "/magaza/", "/kampanya/"),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?pazarama\.com/[^"'<>\s]+-p-[^"'<>\s]+)["']''',
        r'''["'](?P<url>/[^"'<>\s]+-p-[^"'<>\s]+)["']''',
        r'''["'](?:productUrl|seoUrl|url)["']\s*:\s*["'](?P<url>/[^"']+(?:-p-|/urun/)[^"']*)["']''',
    ),
)
