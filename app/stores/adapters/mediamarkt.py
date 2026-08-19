from __future__ import annotations

from app.stores.adapters.base import StoreAdapter

MEDIAMARKT_ADAPTER = StoreAdapter(
    code="mediamarkt",
    selectors=(
        "[data-test='mms-search-srp-productlist-item']",
        "[data-test*='product-list-item']",
        "article[data-product-id]",
        "[data-product-number]",
        "a[href*='/tr/product/_']",
        "a[href*='/tr/product/']",
    ),
    excluded_path_tokens=(
        "/search", "/category/", "/brand/", "/campaign/", "/services/",
    ),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?mediamarkt\.com\.tr/tr/product/_[^"'<>\s]+\.html[^"'<>\s]*)["']''',
        r'''["'](?P<url>/tr/product/_[^"'<>\s]+\.html[^"'<>\s]*)["']''',
        r'''["'](?:url|productUrl|canonicalUrl)["']\s*:\s*["'](?P<url>/tr/product/[^"']+)["']''',
    ),
)
