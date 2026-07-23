from types import SimpleNamespace

from app.database.database import SessionLocal
from app.database.models import (
    OfferPriceHistory,
    ProductDB,
    ProductGroup,
    ProductOffer,
    Store,
)
from app.services.multi_store_service import sync_product_offer


def build_product_object(
    database_product: ProductDB,
) -> SimpleNamespace:
    """
    ProductDB kaydını sync_product_offer fonksiyonunun
    kullanabileceği ürün nesnesine dönüştürür.
    """

    return SimpleNamespace(
        name=database_product.name,
        price=database_product.price,
        old_price=database_product.old_price,
        rating=database_product.rating,
        review_count=database_product.review_count,
        seller=database_product.seller,
        url=database_product.url,
        image=database_product.image,
        brand=getattr(
            database_product,
            "brand",
            None,
        ),
        model=getattr(
            database_product,
            "model",
            None,
        ),
        category=getattr(
            database_product,
            "category",
            None,
        ),
        description=getattr(
            database_product,
            "description",
            None,
        ),
        specifications=getattr(
            database_product,
            "specifications",
            None,
        ),
        stock_status=getattr(
            database_product,
            "stock_status",
            None,
        ),
        source_site=getattr(
            database_product,
            "source_site",
            None,
        ),
        product_code=getattr(
            database_product,
            "product_code",
            None,
        ),
    )


def print_database_counts(db) -> None:
    """
    Çoklu mağaza tablolarındaki mevcut kayıt sayılarını yazdırır.
    """

    print()
    print("=" * 60)
    print("VERİTABANI DURUMU")
    print("=" * 60)

    print(
        "Products:",
        db.query(ProductDB).count(),
    )

    print(
        "Stores:",
        db.query(Store).count(),
    )

    print(
        "Groups:",
        db.query(ProductGroup).count(),
    )

    print(
        "Offers:",
        db.query(ProductOffer).count(),
    )

    print(
        "Offer History:",
        db.query(OfferPriceHistory).count(),
    )


def backfill_multi_store() -> None:
    """
    ProductOffer kaydı bulunmayan eski ürünleri çoklu
    mağaza tablolarına aktarır.

    Mevcut tekliflere dokunmaz ve aynı ürün için ikinci
    ProductOffer kaydı oluşturmaz.
    """

    db = SessionLocal()

    processed_count = 0
    skipped_count = 0
    error_count = 0

    try:
        products = (
            db.query(ProductDB)
            .order_by(ProductDB.id.asc())
            .all()
        )

        print_database_counts(db)

        print()
        print("=" * 60)
        print("ÇOKLU MAĞAZA BACKFILL BAŞLIYOR")
        print("=" * 60)
        print("Toplam ürün:", len(products))

        for index, database_product in enumerate(
            products,
            start=1,
        ):
            existing_offer = (
                db.query(ProductOffer)
                .filter(
                    ProductOffer.product_id
                    == database_product.id
                )
                .first()
            )

            if existing_offer:
                skipped_count += 1

                print()
                print(
                    f"[{index}/{len(products)}] "
                    f"Atlandı: teklif zaten mevcut"
                )

                print(
                    "Ürün ID:",
                    database_product.id,
                )

                print(
                    "Ürün:",
                    database_product.name,
                )

                continue

            print()
            print(
                f"[{index}/{len(products)}] "
                f"Aktarılıyor..."
            )

            print(
                "Ürün ID:",
                database_product.id,
            )

            print(
                "Ürün:",
                database_product.name,
            )

            try:
                product = build_product_object(
                    database_product
                )

                offer = sync_product_offer(
                    db=db,
                    database_product=database_product,
                    product=product,
                    price_changed=True,
                )

                db.commit()

                processed_count += 1

                print(
                    "Aktarım başarılı. Offer ID:",
                    offer.id,
                )

            except Exception as product_error:
                db.rollback()

                error_count += 1

                print(
                    "Ürün aktarım hatası:",
                    type(product_error).__name__,
                    product_error,
                )

        print()
        print("=" * 60)
        print("BACKFILL TAMAMLANDI")
        print("=" * 60)
        print("Aktarılan:", processed_count)
        print("Atlanan:", skipped_count)
        print("Hatalı:", error_count)

        print_database_counts(db)

    except Exception as error:
        db.rollback()

        print()
        print(
            "Backfill genel hatası:",
            type(error).__name__,
            error,
        )

        raise

    finally:
        db.close()


if __name__ == "__main__":
    backfill_multi_store()