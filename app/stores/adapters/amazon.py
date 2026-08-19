from __future__ import annotations

from app.stores.adapters.base import StoreAdapter

AMAZON_ADAPTER = StoreAdapter(
    code="amazon",
    selectors=(
        "[data-component-type='s-search-result'][data-asin]",
        "div.s-result-item[data-asin]",
        "[data-cel-widget^='search_result_']",
        "h2 a[href*='/dp/']",
        "a.a-link-normal[href*='/dp/']",
        "a[href*='/gp/product/']",
    ),
    excluded_path_tokens=(
        "/gp/help/", "/hz/", "/stores/", "/b/", "/s?", "/customer/",
    ),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?amazon\.com\.tr/(?:[^"'<>\s]+/)?dp/[A-Z0-9]{10}(?:[^"'<>\s]*)?)["']''',
        r'''["'](?P<url>/(?:[^"'<>\s]+/)?dp/[A-Z0-9]{10}(?:[^"'<>\s]*)?)["']''',
        r'''["'](?P<url>/gp/product/[A-Z0-9]{10}(?:[^"'<>\s]*)?)["']''',
    ),
)
