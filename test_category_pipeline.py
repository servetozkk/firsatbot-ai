from app.category_scrapers.registry import CategoryScraperRegistry
from app.services.category_discovery_service import CategoryDiscoveryService


TEST_URLS = {
    "teknosa": "https://www.teknosa.com/cep-telefonu-c-100001",
    "trendyol": "https://www.trendyol.com/oyuncu-mouselari-x-c106088",
}


def main() -> None:
    registry = CategoryScraperRegistry()
    print("Desteklenen kategori mağazaları:", registry.list_stores())

    for store_code, url in TEST_URLS.items():
        print()
        print("=" * 70)
        print("TEST:", store_code)
        scraper = registry.get_scraper(url)
        result = scraper.collect_product_links(
            category_url=url,
            limit=5,
            max_pages=2,
        )
        print("Sayfa:", result.visited_page_count)
        print("Link:", result.found_count)
        for link in result.links:
            print("-", link.url)

    # Gerçek ürün kaydı için aşağıdaki satır kullanılabilir:
    # print(CategoryDiscoveryService().scan_and_save(TEST_URLS["teknosa"], 5, 2))


if __name__ == "__main__":
    main()
