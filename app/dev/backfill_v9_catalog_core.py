from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal, create_db
from app.database.models import ProductDB
from app.models.product import Product
from app.services.global_catalog_service import sync_raw_and_global_catalog
from app.services.product_identity_service import ProductIdentityService


def _specifications(value):
    if not value:
        return None
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def main() -> int:
    create_db()
    db = SessionLocal()
    processed = 0
    failed = 0

    try:
        products = (
            db.query(ProductDB)
            .execution_options(include_deleted=True)
            .filter(ProductDB.is_deleted.is_(False))
            .order_by(ProductDB.id.asc())
            .all()
        )

        for item in products:
            try:
                product = Product(
                    name=item.name,
                    price=float(item.price),
                    old_price=item.old_price,
                    rating=item.rating,
                    review_count=item.review_count,
                    seller=item.seller or item.source_site or "Bilinmiyor",
                    url=item.url,
                    image=item.image,
                    image_gallery=item.image_gallery,
                    brand=item.brand,
                    model=item.model,
                    category=item.category,
                    description=item.description,
                    specifications=_specifications(item.specifications),
                    stock_status=item.stock_status,
                    source_site=item.source_site,
                    product_code=item.product_code,
                )
                product = ProductIdentityService.enrich_product(product)
                identity = ProductIdentityService.explain(product)
                sync_raw_and_global_catalog(
                    db=db,
                    product=product,
                    legacy_product_id=item.id,
                    identity_info=identity,
                )
                processed += 1
                if processed % 100 == 0:
                    db.commit()
                    print(f"İşlenen eski ürün: {processed}")
            except Exception as error:
                failed += 1
                print(
                    f"BACKFILL HATASI product_id={item.id}: "
                    f"{type(error).__name__}: {error}"
                )

        db.commit()
        print(f"OK  Ham havuza taşınan ürün: {processed}")
        print(f"OK  Atlanan/hatalı ürün: {failed}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
