from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal, create_db
from app.database.models import GlobalOffer
from app.services.global_price_history_service import record_global_offer_price


def main() -> int:
    create_db()
    db = SessionLocal()
    processed = 0
    try:
        offers = db.query(GlobalOffer).order_by(GlobalOffer.id.asc()).all()
        for offer in offers:
            record_global_offer_price(
                db=db,
                offer=offer,
                checked_at=offer.last_seen_at or offer.updated_at,
                force=True,
            )
            processed += 1
        db.commit()
        print(f"OK  Başlangıç fiyat kaydı işlenen teklif: {processed}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
