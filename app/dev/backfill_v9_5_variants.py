from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, GlobalProductVariant, RawProduct

def main() -> int:
    db = SessionLocal(); assigned = 0; created = 0
    try:
        offers = db.query(GlobalOffer).filter(GlobalOffer.global_variant_id.is_(None)).order_by(GlobalOffer.id.asc()).all()
        for offer in offers:
            raw = db.get(RawProduct, offer.raw_product_id)
            product = db.get(GlobalProduct, offer.global_product_id)
            if raw is None or product is None:
                continue
            variant = db.query(GlobalProductVariant).filter(GlobalProductVariant.global_product_id == product.id, GlobalProductVariant.variant_key == "default").first()
            if variant is None:
                variant = GlobalProductVariant(global_product_id=product.id, variant_key="default", primary_image=raw.image_raw or product.primary_image)
                db.add(variant); db.flush(); created += 1
            offer.global_variant_id = variant.id
            raw.global_variant_id = variant.id
            assigned += 1
        db.commit()
        print(f"OK  Varsayılan varyanta bağlanan teklif: {assigned}")
        print(f"OK  Oluşturulan varsayılan varyant: {created}")
        return 0
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
if __name__ == "__main__":
    raise SystemExit(main())
