import time

from app.database.database import SessionLocal
from app.database.models import ProductDB
from app.scrapers.trendyol import TrendyolScraper
from app.services.product_service import save_product


REQUEST_DELAY_SECONDS = 2


def get_trendyol_urls() -> list[str]:
    db = SessionLocal()

    try:
        products = (
            db.query(ProductDB)
            .filter(ProductDB.url.contains("trendyol.com"))
            .order_by(ProductDB.id.asc())
            .all()
        )

        return [
            product.url
            for product in products
            if product.url
        ]

    finally:
        db.close()


def main() -> None:
    scraper = TrendyolScraper()
    urls = get_trendyol_urls()

    total = len(urls)
    success_count = 0
    failed_count = 0

    print()
    print("Trendyol ürün yenileme işlemi başladı.")
    print("Toplam ürün:", total)
    print()

    for index, url in enumerate(urls, start=1):
        print("=" * 80)
        print(f"[{index}/{total}] Ürün yenileniyor")
        print(url)

        try:
            product = scraper.scrape(url)

            if product is None:
                print("Ürün bilgisi alınamadı.")
                failed_count += 1
                continue

            save_product(product)

            success_count += 1
            print("Ürün başarıyla güncellendi.")

        except KeyboardInterrupt:
            print()
            print("İşlem kullanıcı tarafından durduruldu.")
            break

        except Exception as error:
            failed_count += 1

            print(
                "Ürün güncelleme hatası:",
                type(error).__name__,
                str(error),
            )

        if index < total:
            time.sleep(REQUEST_DELAY_SECONDS)

    print()
    print("=" * 80)
    print("Yenileme işlemi tamamlandı.")
    print("Başarılı:", success_count)
    print("Başarısız:", failed_count)
    print("Toplam:", total)


if __name__ == "__main__":
    main()