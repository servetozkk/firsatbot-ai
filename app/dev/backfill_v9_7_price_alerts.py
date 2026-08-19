from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal, create_db
from app.database.models import GlobalPriceAlert, PriceAlert, ProductGroup, GlobalProduct


def main() -> int:
    create_db()
    db = SessionLocal()
    migrated = 0
    skipped = 0
    try:
        rows = (
            db.query(PriceAlert, ProductGroup)
            .join(ProductGroup, ProductGroup.id == PriceAlert.product_group_id)
            .filter(PriceAlert.is_active.is_(True))
            .all()
        )
        for old, group in rows:
            product = (
                db.query(GlobalProduct)
                .filter(GlobalProduct.identity_key == group.group_key)
                .first()
            )
            if product is None:
                skipped += 1
                continue

            existing = (
                db.query(GlobalPriceAlert)
                .filter(
                    GlobalPriceAlert.visitor_id == old.visitor_id,
                    GlobalPriceAlert.global_product_id == product.id,
                    GlobalPriceAlert.global_variant_id.is_(None),
                )
                .first()
            )
            if existing is None:
                db.add(
                    GlobalPriceAlert(
                        visitor_id=old.visitor_id,
                        global_product_id=product.id,
                        global_variant_id=None,
                        target_price=float(old.target_price),
                        is_active=bool(old.is_active),
                        created_at=old.created_at,
                        updated_at=old.updated_at,
                    )
                )
                migrated += 1

        db.commit()
        print(f"OK  Global alarma taşınan eski alarm: {migrated}")
        print(f"OK  Global ürünü olmadığı için atlanan: {skipped}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
