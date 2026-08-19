from __future__ import annotations

from app.database.database import SessionLocal
from app.database.models import ProductDB, ProductGroup, ProductOffer
from app.services.multi_store_service import sync_product_features
from app.services.product_attribute_extractor import ProductAttributeExtractor


def main() -> None:
    """Mevcut ürün başlıklarından çıkarılan teknik özellikleri gruplara yazar."""
    db = SessionLocal()
    processed = saved = skipped = failed = 0

    try:
        rows = (
            db.query(ProductDB, ProductOffer, ProductGroup)
            .join(ProductOffer, ProductOffer.product_id == ProductDB.id)
            .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
            .all()
        )
        print("Akıllı veri backfill işlemi başlıyor.")
        print("İşlenecek ürün:", len(rows))
        print("-" * 70)

        for product, _offer, group in rows:
            processed += 1
            try:
                extracted = ProductAttributeExtractor.extract(
                    name=product.name,
                    description=product.description,
                    specifications=product.specifications,
                    category=group.category or product.category,
                    brand=group.brand or product.brand,
                    model=group.model or product.model,
                )
                if not extracted.sections:
                    skipped += 1
                    continue
                count = sync_product_features(
                    db=db,
                    product_group=group,
                    specifications=extracted.as_specifications(),
                    source="title-parser-v1",
                )
                saved += count
                print(
                    f"[TAMAM] Ürün #{product.id} -> Grup #{group.id}: "
                    f"{count} özellik, güven %{extracted.confidence}"
                )
            except Exception as error:
                failed += 1
                print(f"[HATA] Ürün #{product.id}: {error}")

        db.commit()
        print("-" * 70)
        print("Backfill tamamlandı.")
        print("İşlenen:", processed)
        print("Kaydedilen/güncellenen özellik:", saved)
        print("Atlanan:", skipped)
        print("Hatalı:", failed)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
