from __future__ import annotations

from app.database.database import SessionLocal
from app.database.models import (
    ProductDB,
    ProductGroup,
    ProductOffer,
)
from app.services.multi_store_service import (
    sync_product_features,
)


def main() -> None:
    """
    Products tablosundaki mevcut specifications verilerini,
    bağlı oldukları ürün gruplarının teknik özellik tablolarına aktarır.
    """
    db = SessionLocal()

    processed_products = 0
    saved_features = 0
    skipped_products = 0
    failed_products = 0

    try:
        rows = (
            db.query(
                ProductDB,
                ProductOffer,
                ProductGroup,
            )
            .join(
                ProductOffer,
                ProductOffer.product_id == ProductDB.id,
            )
            .join(
                ProductGroup,
                ProductGroup.id == ProductOffer.group_id,
            )
            .filter(
                ProductDB.specifications.isnot(None),
                ProductDB.specifications != "",
            )
            .all()
        )

        print("Teknik özellik backfill işlemi başlıyor.")
        print("İşlenecek ürün:", len(rows))
        print("-" * 70)

        for database_product, offer, product_group in rows:
            processed_products += 1

            try:
                count = sync_product_features(
                    db=db,
                    product_group=product_group,
                    specifications=database_product.specifications,
                    source=database_product.source_site,
                )

                if count == 0:
                    skipped_products += 1
                    print(
                        f"[ATLANDI] Ürün #{database_product.id}: "
                        "özellik verisi ayrıştırılamadı."
                    )
                    continue

                saved_features += count
                print(
                    f"[TAMAM] Ürün #{database_product.id} -> "
                    f"Grup #{product_group.id}: {count} özellik"
                )

            except Exception as error:
                failed_products += 1
                print(
                    f"[HATA] Ürün #{database_product.id}: {error}"
                )

        db.commit()

        print("-" * 70)
        print("Backfill tamamlandı.")
        print("İşlenen ürün:", processed_products)
        print("Kaydedilen/güncellenen özellik:", saved_features)
        print("Atlanan ürün:", skipped_products)
        print("Hatalı ürün:", failed_products)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
