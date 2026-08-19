from __future__ import annotations

from app.stores.adapters.base import StoreAdapter


TURKCELL_PASAJ_ADAPTER = StoreAdapter(
    code="turkcellpasaj",
    selectors=(
        "a[href*='/pasaj/cep-telefonu/']",
        "a[href*='/pasaj/bilgisayar-tablet/']",
        "a[href*='/pasaj/tv-ses-sistemleri/']",
        "a[href*='/pasaj/elektrikli-ev-aletleri/']",
        "[data-product-url]",
        "[data-testid*='product'] a[href]",
        "[class*='product'] a[href]",
    ),
    excluded_exact_paths=("/pasaj", "/pasaj/"),
    excluded_path_tokens=(
        "/pasaj/c/",
        "/pasaj/magaza/",
        "/pasaj/marka/",
        "/pasaj/kampanya",
        "/pasaj/hesabim",
        "/pasaj/sepet",
        "/pasaj/favori",
        "/pasaj/yardim",
        "/pasaj/blog",
    ),
    html_href_patterns=(
        r'''["'](?P<url>https?://(?:www\.)?turkcell\.com\.tr/pasaj/(?:cep-telefonu|bilgisayar-tablet|tv-ses-sistemleri|elektrikli-ev-aletleri|saglik-kisisel-bakim|hobi-oyun|ev-yasam)/[^"'<>\s?#]+/[^"'<>\s?#]+)["']''',
        r'''["'](?P<url>/pasaj/(?:cep-telefonu|bilgisayar-tablet|tv-ses-sistemleri|elektrikli-ev-aletleri|saglik-kisisel-bakim|hobi-oyun|ev-yasam)/[^"'<>\s?#]+/[^"'<>\s?#]+)["']''',
        r'''["'](?:productUrl|seoUrl|url)["']\s*:\s*["'](?P<url>/pasaj/(?:cep-telefonu|bilgisayar-tablet|tv-ses-sistemleri|elektrikli-ev-aletleri|saglik-kisisel-bakim|hobi-oyun|ev-yasam)/[^"']+)["']''',
    ),
)
