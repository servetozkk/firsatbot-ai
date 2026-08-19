from __future__ import annotations
from urllib.parse import urlsplit
from app.stores.adapters.base import StoreAdapter

class VatanAdapter(StoreAdapter):
    def accept_url(self, url: str) -> bool:
        if not super().accept_url(url):
            return False
        path=(urlsplit(url).path or '/').casefold()
        return path.endswith('.html') and '/arama/' not in path

VATAN_ADAPTER=VatanAdapter(
    code='vatan',
    selectors=(".product-list a[href$='.html']", ".product-item a[href$='.html']", "a[href$='.html']"),
    excluded_path_tokens=("/arama/","/kategori/","/marka/","/kampanya/","/hizmetler/"),
    html_href_patterns=(r'''["'](?P<url>https?://(?:www\.)?vatanbilgisayar\.com/[^"'<>\s]+\.html)["']''',r'''["'](?P<url>/[^"'<>\s]+\.html)["']'''),
)
