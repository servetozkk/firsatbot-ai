from __future__ import annotations
from urllib.parse import urlsplit
from app.stores.adapters.base import StoreAdapter

class IncehesapAdapter(StoreAdapter):
    def accept_url(self,url:str)->bool:
        if not super().accept_url(url): return False
        path=(urlsplit(url).path or '/').casefold()
        return '-fiyati-' in path or path.startswith('/urun/')

INCEHESAP_ADAPTER=IncehesapAdapter(
 code='incehesap',
 selectors=("a[href*='-fiyati-']","a[href^='/urun/']",".product-list a[href]",".product-item a[href]"),
 excluded_path_tokens=("/cozum-merkezi","/gaming-geceleri","/q/","/ara/","/kategori/","/marka/","/uye/","/icerik/"),
 html_href_patterns=(r'''["'](?P<url>https?://(?:www\.)?incehesap\.com/[^"'<>\s]*-fiyati-[^"'<>\s]+/?)['"]''',r'''["'](?P<url>/[^"'<>\s]*-fiyati-[^"'<>\s]+/?)['"]'''),
)
