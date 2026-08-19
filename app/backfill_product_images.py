from __future__ import annotations

import argparse
import time

import requests

from app.database.database import SessionLocal
from app.database.migrations import migrate_database
from app.database.models import ProductDB
from app.services.product_image_service import collect_image_urls, parse_image_gallery, serialize_image_gallery, persist_product_images

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Mevcut ürün galerilerini temizler ve ürün sayfalarından kaliteli görselleri toplar.")
    parser.add_argument("--limit", type=int, default=500, help="İşlenecek en fazla ürün sayısı")
    parser.add_argument("--delay", type=float, default=0.35, help="İstekler arası bekleme süresi")
    parser.add_argument("--force", action="store_true", help="Galerisi olan ürünleri de yeniden tara")
    parser.add_argument("--clean-only", action="store_true", help="Ağa çıkmadan kayıtlı galerilerdeki logo/ikon/banner görsellerini temizle")
    args = parser.parse_args()

    # Komut doğrudan çalıştırıldığında da image_gallery sütunu eksik kalmasın.
    migrate_database()

    db = SessionLocal()
    processed = updated = failed = removed = 0
    try:
        products = (
            db.query(ProductDB)
            .order_by(ProductDB.updated_at.desc(), ProductDB.id.desc())
            .limit(max(1, args.limit))
            .all()
        )
        session = requests.Session()
        session.headers.update(HEADERS)

        for product in products:
            raw_gallery = getattr(product, "image_gallery", None)
            current = parse_image_gallery(raw_gallery)
            raw_count = 0
            if raw_gallery:
                try:
                    import json
                    parsed = json.loads(raw_gallery)
                    raw_count = len(parsed) if isinstance(parsed, list) else 0
                except Exception:
                    raw_count = 0

            if args.clean_only:
                processed += 1
                cleaned = current
                removed += max(0, raw_count - len(cleaned))
                product.image_gallery = serialize_image_gallery(cleaned)
                if cleaned and (not product.image or product.image not in cleaned):
                    product.image = cleaned[0]
                persist_product_images(
                    db,
                    product_id=product.id,
                    primary=product.image,
                    gallery=cleaned,
                    source=product.source_site,
                    replace=True,
                )
                db.commit()
                if raw_count != len(cleaned):
                    updated += 1
                    print(f"TEMİZLENDİ {product.name[:65]}: {raw_count} -> {len(cleaned)}")
                continue

            if current and not args.force:
                continue
            processed += 1
            try:
                response = session.get(product.url, timeout=25, allow_redirects=True)
                response.raise_for_status()
                images = collect_image_urls(
                    response.text,
                    primary=product.image,
                    base_url=response.url,
                    limit=60,
                )
                if images:
                    product.image_gallery = serialize_image_gallery(images)
                    product.image = images[0]
                    persist_product_images(
                        db,
                        product_id=product.id,
                        primary=product.image,
                        gallery=images,
                        source=product.source_site,
                        replace=False,
                    )
                    updated += 1
                    print(f"[{updated}] {product.name[:70]} -> {len(images)} kaliteli görsel")
                else:
                    # Eski galerideki geçerli ana görseli koru.
                    fallback = current or ([product.image] if product.image else [])
                    product.image_gallery = serialize_image_gallery(fallback)
                    persist_product_images(
                        db,
                        product_id=product.id,
                        primary=product.image,
                        gallery=fallback,
                        source=product.source_site,
                        replace=False,
                    )
                    print(f"[0] {product.name[:70]} -> uygun ürün görseli bulunamadı")
                db.commit()
            except Exception as exc:
                db.rollback()
                failed += 1
                print(f"HATA product_id={product.id}: {exc}")
            time.sleep(max(0, args.delay))
    finally:
        db.close()

    print("\nGörsel işlemi tamamlandı.")
    print({"processed": processed, "updated": updated, "removed": removed, "failed": failed})


if __name__ == "__main__":
    main()
