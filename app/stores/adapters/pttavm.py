from __future__ import annotations

from app.stores.adapters.base import StoreAdapter

PTTAVM_ADAPTER = StoreAdapter(
    code="pttavm",
    selectors=(
        "a[href*='-p-']",
        "[data-product-url]",
        "[data-testid*='product'] a[href]",
        "[class*='product'] a[href]",
    ),
    excluded_path_tokens=("/arama", "/kategori/", "/magaza/", "/kampanya/", "/kupon/"),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?pttavm\.com/[^"'<>\s]+-p-\d+(?:\?[^"'<>\s]*)?)["']''',
        r'''["'](?P<url>/[^"'<>\s]+-p-\d+(?:\?[^"'<>\s]*)?)["']''',
        r'''["'](?:productUrl|seoUrl|url)["']\s*:\s*["'](?P<url>/[^"']+-p-\d+[^"']*)["']''',
    ),
)
