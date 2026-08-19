from __future__ import annotations

import json
from collections import defaultdict

from app.database.database import SessionLocal
from app.database.models import ProductDB, ProductGroup, ProductOffer
from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService


def _product_from_row(row: ProductDB) -> Product:
    specs = row.specifications
    if isinstance(specs, str) and specs.strip().startswith(("{", "[")):
        try:
            specs = json.loads(specs)
        except (json.JSONDecodeError, TypeError):
            pass
    return Product(
        name=row.name,
        price=float(row.price or 0),
        old_price=row.old_price,
        rating=row.rating,
        review_count=row.review_count,
        seller=row.seller or row.source_site or "Bilinmiyor",
        url=row.url,
        image=row.image,
        image_gallery=row.image_gallery,
        brand=row.brand,
        model=row.model,
        category=row.category,
        description=row.description,
        specifications=specs,
        stock_status=row.stock_status,
        source_site=row.source_site,
        product_code=row.product_code,
    )


def _offer_group_id(offer: ProductOffer) -> int | None:
    """Eski/yeni model adlarını birlikte destekle."""
    value = getattr(offer, "group_id", None)
    if value is None:
        value = getattr(offer, "product_group_id", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    db = SessionLocal()
    changed_products = 0
    changed_groups = 0
    skipped_offers = 0
    try:
        rows = db.query(ProductDB).execution_options(include_deleted=True).all()
        group_candidates: dict[int, list[Product]] = defaultdict(list)
        product_ids = {row.id: row for row in rows}

        offers = db.query(ProductOffer).all()
        for offer in offers:
            row = product_ids.get(offer.product_id)
            group_id = _offer_group_id(offer)
            if row is None or group_id is None:
                skipped_offers += 1
                continue
            group_candidates[group_id].append(_product_from_row(row))

        for row in rows:
            product = _product_from_row(row)
            ProductIdentityService.enrich_product(product)
            dirty = False
            if product.brand and product.brand != row.brand:
                row.brand = product.brand
                dirty = True
            if product.model and product.model != row.model:
                row.model = product.model
                dirty = True
            if dirty:
                changed_products += 1

        for group_id, products in group_candidates.items():
            group = db.query(ProductGroup).filter(ProductGroup.id == group_id).first()
            if group is None or not products:
                continue
            best = max(
                products,
                key=lambda item: (
                    bool(item.brand),
                    bool(item.model),
                    len(str(item.model or "")),
                    len(str(item.name or "")),
                ),
            )
            ProductIdentityService.enrich_product(best)
            dirty = False
            if best.brand and best.brand.casefold() != str(group.brand or "").casefold():
                group.brand = ProductIdentityService.normalize_token(best.brand)
                dirty = True
            if best.model and best.model.casefold() != str(group.model or "").casefold():
                group.model = ProductIdentityService.normalize_token(best.model)
                dirty = True
            if dirty:
                changed_groups += 1

        db.commit()
        print(
            "Product Parser v2 backfill tamamlandı. "
            f"Ürün: {changed_products}, grup: {changed_groups}, atlanan teklif: {skipped_offers}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
