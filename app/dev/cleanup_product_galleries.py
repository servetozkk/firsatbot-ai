from __future__ import annotations

from app.database.database import SessionLocal
from app.database.models import ProductDB
from app.services.product_image_service import (
    canonical_image_key,
    dedupe_image_urls,
    parse_image_gallery,
    serialize_image_gallery,
)


def main() -> None:
    db = SessionLocal()
    changed_products = 0
    removed_rows = 0
    try:
        products = db.query(ProductDB).all()
        product_ids = [row.id for row in products]

        # Eski JSON galerilerini yeni filtre ile yeniden temizle.
        for product in products:
            values = ([product.image] if getattr(product, "image", None) else [])
            values += parse_image_gallery(getattr(product, "image_gallery", None))
            cleaned = dedupe_image_urls(values, primary=getattr(product, "image", None), limit=40)
            old = parse_image_gallery(getattr(product, "image_gallery", None))
            if cleaned != old:
                product.image_gallery = serialize_image_gallery(cleaned)
                changed_products += 1
            if cleaned:
                primary = getattr(product, "image", None)
                primary_clean = dedupe_image_urls([primary], primary=primary, limit=1) if primary else []
                if not primary_clean:
                    product.image = cleaned[0]

        # Kalıcı product_images tablosu varsa geçersiz satırları temizle.
        try:
            from app.database.models import ProductImage
            rows = db.query(ProductImage).filter(ProductImage.product_id.in_(product_ids)).all() if product_ids else []
            by_product: dict[int, list] = {}
            for row in rows:
                by_product.setdefault(int(row.product_id), []).append(row)

            for product_id, image_rows in by_product.items():
                product = next((p for p in products if p.id == product_id), None)
                primary = getattr(product, "image", None) if product else None
                cleaned = dedupe_image_urls([r.image_url for r in image_rows], primary=primary, limit=40)
                allowed = {canonical_image_key(url): url for url in cleaned}
                seen: set[str] = set()
                order = 0
                for row in sorted(image_rows, key=lambda r: (not bool(getattr(r, "is_primary", False)), getattr(r, "sort_order", 0), r.id)):
                    key = canonical_image_key(row.image_url)
                    if key not in allowed or key in seen:
                        db.delete(row)
                        removed_rows += 1
                        continue
                    seen.add(key)
                    row.image_url = allowed[key]
                    row.sort_order = order
                    row.is_primary = order == 0
                    if hasattr(row, "canonical_key"):
                        row.canonical_key = key
                    order += 1
        except (ImportError, AttributeError):
            pass

        db.commit()
        print(f"Galeri temizliği tamamlandı. Güncellenen ürün: {changed_products}, silinen gereksiz görsel satırı: {removed_rows}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
