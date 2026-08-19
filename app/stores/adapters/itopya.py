from __future__ import annotations
import re
from urllib.parse import urlsplit
from app.stores.adapters.base import StoreAdapter

class ItopyaAdapter(StoreAdapter):
    def accept_url(self,url:str)->bool:
        if not super().accept_url(url): return False
        path=(urlsplit(url).path or '/').casefold().rstrip('/')
        if re.search(r'_k\d+$',path): return False
        return '/urun/' in path or bool(re.search(r'_u\d+$',path))

ITOPYA_ADAPTER=ItopyaAdapter(
 code='itopya',
 selectors=("a[href*='/urun/']","a[href*='_u']",".product a[href]",".product-item a[href]"),
 excluded_path_tokens=("/aramasonuclari.aspx","/islemci_","/anakart_","/ekran-karti_","/rambellek_","/kategori/","/kampanya/"),
 html_href_patterns=(r'''["'](?P<url>https?://(?:www\.)?itopya\.com/(?:urun/[^"'<>\s]+|[^"'<>\s]+_u\d+))["']''',r'''["'](?P<url>/(?:urun/[^"'<>\s]+|[^"'<>\s]+_u\d+))["']'''),
)
