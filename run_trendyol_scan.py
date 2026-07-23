from app.database.database import create_db
from app.scrapers.trendyol import TrendyolScraper
from app.services.product_service import save_product


CATEGORY_URL = "https://www.trendyol.com/oyuncu-mouselari-x-c106088"
PRODUCT_LIMIT = 10


def main():
    print("Veritabanı hazırlanıyor...")
    create_db()

    scraper = TrendyolScraper()

    print("Kategori taraması başlıyor...")

    products = scraper.scrape_category(
        category_url=CATEGORY_URL,
        limit=PRODUCT_LIMIT,
    )

    print()
    print("=" * 70)
    print("VERİTABANINA KAYIT BAŞLIYOR")
    print("=" * 70)

    saved_count = 0
    failed_count = 0

    for number, product in enumerate(products, start=1):
        print()
        print(f"[{number}/{len(products)}] Kaydediliyor:")
        print(product.name)

        try:
            save_product(product)
            saved_count += 1

        except Exception as error:
            failed_count += 1
            print("Kayıt sırasında hata oluştu:", error)

    print()
    print("=" * 70)
    print("TARAMA TAMAMLANDI")
    print("=" * 70)
    print("Okunan ürün:", len(products))
    print("Kaydedilen/güncellenen:", saved_count)
    print("Hatalı:", failed_count)


if __name__ == "__main__":
    main()
