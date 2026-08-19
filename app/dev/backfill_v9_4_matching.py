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
    matched = review = failed = 0
    try:
        rows = (
            db.query(RawProduct)
            .filter(
                RawProduct.reconciliation_status.in_(
                    ["PENDING", "FAILED", "REVIEW_REQUIRED"]
                )
            )
            .order_by(RawProduct.id.asc())
            .limit(5000)
            .all()
        )
        for raw in rows:
            success, _message = reconcile_raw_product(db=db, raw=raw)
            if success:
                matched += 1
            elif raw.reconciliation_status == "REVIEW_REQUIRED":
                review += 1
            else:
                failed += 1
        db.commit()
        print(f"OK  Otomatik eşleşen: {matched}")
        print(f"OK  İnceleme kuyruğuna alınan: {review}")
        print(f"OK  Hatalı: {failed}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
