from app.database.database import SessionLocal
from app.database.models import ProductDB
from app.services.data_integrity_service import stable_product_key, sync_persistent_gallery
from app.services.product_image_service import parse_image_gallery

def main():
    db=SessionLocal()
    try:
        rows=db.query(ProductDB).execution_options(include_deleted=True).all()
        for row in rows:
            if not row.stable_key:
                row.stable_key=stable_product_key(identity_key=None, product_code=row.product_code, url=row.url, name=row.name)
            sync_persistent_gallery(db, product=row, values=parse_image_gallery(row.image_gallery), source_store=row.source_site or row.seller)
        db.commit()
        print(f"v7.0 veri motoru hazırlandı. Ürün: {len(rows)}")
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
if __name__ == "__main__": main()
