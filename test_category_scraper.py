from app.scrapers.trendyol import TrendyolScraper


CATEGORY_URL = "https://www.trendyol.com/oyuncu-mouselari-x-c106088"


def main():
    scraper = TrendyolScraper()

    links = scraper.get_product_links(
        category_url=CATEGORY_URL,
        limit=10,
    )

    print()
    print("=" * 70)
    print("BULUNAN ÜRÜN BAĞLANTILARI")
    print("=" * 70)

    for number, link in enumerate(links, start=1):
        print(f"{number}. {link}")

    print()
    print("Toplam:", len(links))


if __name__ == "__main__":
    main()
