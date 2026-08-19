from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal, create_db
from app.database.models import RawProduct
from app.services.catalog_reconciliation_service import reconcile_raw_product


def main() -> int:
    create_db()
    db = SessionLocal()
    processed = matched = failed = 0
    try:
        rows = db.query(RawProduct).order_by(RawProduct.id.asc()).all()
        for raw in rows:
            processed += 1
            success, message = reconcile_raw_product(db=db, raw=raw)
            if success:
                matched += 1
            else:
                failed += 1
                print(f"raw={raw.id}: {message}")

            if processed % 100 == 0:
                db.commit()
                print(f"İşlenen ham ürün: {processed}")

        db.commit()
        print(f"OK  İşlenen ham ürün: {processed}")
        print(f"OK  Global teklife bağlanan: {matched}")
        print(f"OK  Hatalı kayıt: {failed}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
