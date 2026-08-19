from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import or_

from app.database.models import AdminAuditLog, DeletedProduct, ProductDB, ProductImage
from app.services.product_image_service import canonical_image_key, dedupe_image_urls, parse_image_gallery


def stable_product_key(*, identity_key: str | None, product_code: str | None, url: str | None, name: str | None) -> str:
    raw = "|".join(str(value or "").strip().casefold() for value in (identity_key, product_code, url, name))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_product_blocked(db, *, url=None, product_code=None, identity_key=None, stable_key=None) -> bool:
    filters = []
    if url: filters.append(DeletedProduct.source_url == str(url).strip())
    if product_code: filters.append(DeletedProduct.product_code == str(product_code).strip())
    if identity_key: filters.append(DeletedProduct.identity_key == str(identity_key).strip())
    if stable_key: filters.append(DeletedProduct.stable_key == str(stable_key).strip())
    if filters and db.query(DeletedProduct.id).filter(or_(*filters)).first():
        return True
    product_filters = []
    if url: product_filters.append(ProductDB.url == str(url).strip())
    if product_code: product_filters.append(ProductDB.product_code == str(product_code).strip())
    if stable_key: product_filters.append(ProductDB.stable_key == str(stable_key).strip())
    if not product_filters:
        return False
    row = (db.query(ProductDB.id)
           .execution_options(include_deleted=True)
           .filter(ProductDB.is_deleted.is_(True), or_(*product_filters)).first())
    return row is not None


def sync_persistent_gallery(db, *, product: ProductDB, values, source_store: str | None = None) -> list[str]:
    incoming = dedupe_image_urls(parse_image_gallery(values), primary=product.image, limit=60)
    if product.image:
        incoming = dedupe_image_urls([product.image, *incoming], primary=product.image, limit=60)
    existing = db.query(ProductImage).filter(ProductImage.product_id == product.id).order_by(ProductImage.sort_order).all()
    merged = dedupe_image_urls([row.image_url for row in existing] + incoming, primary=product.image, limit=60)
    by_key = {row.canonical_key: row for row in existing}
    for index, url in enumerate(merged):
        key = canonical_image_key(url)
        row = by_key.get(key)
        if row is None:
            row = ProductImage(product_id=product.id, image_url=url, canonical_key=key, source_store=source_store)
            db.add(row)
        row.image_url = url
        row.sort_order = index
        row.is_primary = index == 0
        row.quality_score = max(1, 100 - index)
        row.updated_at = datetime.utcnow()
    product.image_gallery = json.dumps(merged, ensure_ascii=False) if merged else product.image_gallery
    if merged and not product.image:
        product.image = merged[0]
    return merged


def record_admin_action(db, *, action: str, entity_type: str, entity_id=None, details=None, actor="admin") -> None:
    db.add(AdminAuditLog(actor=actor, action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id is not None else None, details=json.dumps(details, ensure_ascii=False, default=str) if details is not None else None))
