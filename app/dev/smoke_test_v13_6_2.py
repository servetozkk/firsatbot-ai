from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.sitemap_service import SitemapEntry, sitemap_index_xml, static_entries, urlset_xml


def ok(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.6.2", "VERSION 13.6.2")
    index = sitemap_index_xml("https://example.com", [("/sitemaps/static.xml", None), ("/sitemaps/products-1.xml", None)])
    urlset = urlset_xml("https://example.com", [SitemapEntry("/urun/test-p-abc", priority=.9)])
    ET.fromstring(index)
    ET.fromstring(urlset)
    ok("<sitemapindex" in index, "sitemap index geçerli XML üretiyor")
    ok("https://example.com/sitemaps/products-1.xml" in index, "sitemap index mutlak URL kullanıyor")
    ok("<urlset" in urlset and "<priority>0.9</priority>" in urlset, "URL sitemap geçerli XML üretiyor")
    ok(any(x.path == "/kampanyalar" for x in static_entries()), "kampanya merkezi statik sitemap içinde")
    routes = (ROOT / "app/web/sitemap_routes.py").read_text(encoding="utf-8")
    main_py = (ROOT / "main.py").read_text(encoding="utf-8")
    ok('@router.get("/sitemap.xml"' in routes, "sitemap.xml endpoint mevcut")
    ok("products-{page}.xml" in routes, "ürün sitemap parçalama desteği mevcut")
    ok("sitemap_router" in main_py and "include_router(sitemap_router)" in main_py, "sitemap router uygulamaya bağlı")
    ok("read_only" in routes and "api/sitemap/v13" in routes, "salt okunur sitemap metadata API mevcut")
    print("\nFırsatAI v13.6.2 XML Sitemap smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
