from __future__ import annotations

from app.database.database import SessionLocal, create_db
from app.database.models import (
    Favorite,
    PriceAlert,
    ProductFeatureValue,
    ProductGroup,
    ProductImage,
    ProductOffer,
    ProductReview,
    RecentlyViewed,
    ReviewVote,
    ProductDB,
)
from app.services.product_image_service import persist_product_images


def main() -> None:
    create_db()
    migrated = 0
    orphaned = 0
    db = SessionLocal()
    try:
        products = db.query(ProductDB).all()
        for product in products:
            before = db.query(ProductImage.id).filter(ProductImage.product_id == product.id).count()
            persist_product_images(
                db,
                product_id=product.id,
                primary=product.image,
                gallery=product.image_gallery,
                source=product.source_site,
                replace=False,
            )
            after = db.query(ProductImage.id).filter(ProductImage.product_id == product.id).count()
            if after > before:
                migrated += after - before

        orphan_groups = (
            db.query(ProductGroup)
            .outerjoin(ProductOffer, ProductOffer.group_id == ProductGroup.id)
            .filter(ProductOffer.id.is_(None))
            .all()
        )
        for group in orphan_groups:
            review_ids = [row[0] for row in db.query(ProductReview.id).filter(ProductReview.product_group_id == group.id).all()]
            if review_ids:
                db.query(ReviewVote).filter(ReviewVote.review_id.in_(review_ids)).delete(synchronize_session=False)
            db.query(ProductReview).filter(ProductReview.product_group_id == group.id).delete(synchronize_session=False)
            db.query(ProductFeatureValue).filter(ProductFeatureValue.product_group_id == group.id).delete(synchronize_session=False)
            db.query(Favorite).filter(Favorite.product_group_id == group.id).delete(synchronize_session=False)
            db.query(PriceAlert).filter(PriceAlert.product_group_id == group.id).delete(synchronize_session=False)
            db.query(RecentlyViewed).filter(RecentlyViewed.product_group_id == group.id).delete(synchronize_session=False)
            db.delete(group)
            orphaned += 1

        db.commit()
    finally:
        db.close()

    print("Kalıcı veri onarımı tamamlandı.")
    print({"kalici_gorsel_eklendi": migrated, "bos_grup_temizlendi": orphaned})


if __name__ == "__main__":
    main()
