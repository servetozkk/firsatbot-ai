from __future__ import annotations

import os

from app.category_scrapers.hepsiburada import HepsiburadaCategoryScraper
from app.category_scrapers.registry import CategoryScraperRegistry


SAMPLE_HTML = r'''
<html>
  <body>
    <a href="/samsung-galaxy-s26-256-gb-p-HBCV0000ABC123">Telefon</a>
    <a href="https://www.hepsiburada.com/apple-iphone-17-256-gb-p-HBCV0000XYZ987?magaza=Demo">iPhone</a>
    <a href="/kategori/cep-telefonlari">Kategori</a>
    <script type="application/json">
      {"products":[{"url":"/xiaomi-redmi-note-15-p-HBCV0000QWE456"}]}
    </script>
    <script>window.data={"url":"\/lenovo-ideapad-slim-3-p-HBV0000ASD777"};</script>
  </body>
</html>
'''


def main() -> None:
    scraper = HepsiburadaCategoryScraper()
    registry = CategoryScraperRegistry()

    assert registry.detect_store_code(
        "https://www.hepsiburada.com/cep-telefonlari-c-371965"
    ) == "hepsiburada"

    page_1 = scraper._page_url(
        "https://www.hepsiburada.com/cep-telefonlari-c-371965?filtre=demo",
        1,
    )
    page_2 = scraper._page_url(
        "https://www.hepsiburada.com/cep-telefonlari-c-371965?filtre=demo",
        2,
    )
    assert "sayfa=" not in page_1
    assert "sayfa=2" in page_2

    urls = scraper.extract_product_urls_from_html(SAMPLE_HTML)
    assert len(urls) == 4, urls
    assert all("?" not in url for url in urls)
    assert all(scraper._looks_like_product_url(url) for url in urls)

    print("REGISTRY:", registry.list_stores())
    print("ÇIKARILAN ÜRÜN BAĞLANTISI:", len(urls))
    for url in urls:
        print("-", url)

    live_url = os.getenv("HEPSIBURADA_CATEGORY_URL", "").strip()
    if live_url:
        live_result = scraper.collect_product_links(
            live_url,
            limit=5,
            max_pages=2,
        )
        print("CANLI SAYFA:", live_result.visited_page_count)
        print("CANLI ÜRÜN:", live_result.found_count)
        print("UYARILAR:", live_result.warnings)
        if not live_result.warnings:
            assert live_result.found_count > 0

    print("HEPSİBURADA CATEGORY V1 TESTLERİ BAŞARILI")


if __name__ == "__main__":
    main()
