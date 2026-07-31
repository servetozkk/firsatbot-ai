"""Mevcut products kayıtlarını ürün grubu/teklif tablolarına yeniden bağlar.

Veri silmez. URL başına mevcut ProductOffer kaydını günceller veya eksikse oluşturur.
Çalıştırmadan önce data/products.db dosyasının yedeğini almak önerilir.
"""

from __future__ import annotations

import json

from app.database.database import SessionLocal, create_db
from app.database.models import ProductDB, ProductGroup, ProductOffer
from app.models.product import Product
from app.services.multi_store_service import sync_product_offer


def parse_specifications(value):
    if not value:
        return None
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def to_product(record: ProductDB) -> Product:
    return Product(
        name=record.name,
        price=float(record.price),
        old_price=record.old_price,
        rating=record.rating,
        review_count=record.review_count,
        seller=record.seller or "Bilinmiyor",
        url=record.url,
        image=record.image,
        brand=record.brand,
        model=record.model,
        category=record.category,
        description=record.description,
        specifications=parse_specifications(record.specifications),
        stock_status=record.stock_status,
        source_site=record.source_site,
        product_code=record.product_code,
    )


def main() -> None:
    create_db()
    db = SessionLocal()
    processed = 0
    failed = 0

    try:
        products = db.query(ProductDB).order_by(ProductDB.id).all()
        print(f"İşlenecek mağaza ürün kaydı: {len(products)}")

        for record in products:
            try:
                sync_product_offer(
                    db=db,
                    database_product=record,
                    product=to_product(record),
                    price_changed=False,
                )
                processed += 1
                if processed % 50 == 0:
                    db.commit()
                    print(f"İşlenen: {processed}")
            except Exception as error:
                failed += 1
                db.rollback()
                print(f"Hata - product_id={record.id}: {error}")

        db.commit()
        print("\nBACKFILL TAMAMLANDI")
        print("Başarılı:", processed)
        print("Hatalı:", failed)
        print("Ürün grubu:", db.query(ProductGroup).count())
        print("Teklif:", db.query(ProductOffer).count())
    finally:
        db.close()


if __name__ == "__main__":
    main()
