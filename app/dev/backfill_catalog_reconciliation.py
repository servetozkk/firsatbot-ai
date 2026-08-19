from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from app.database.database import SessionLocal
from app.database.models import ProductOffer
from app.services.multi_store_service import (
    calculate_offer_total_price,
    update_best_offer,
)


def main() -> int:
    db = SessionLocal()
    archived = 0
    repaired = 0
    try:
        offers = db.query(ProductOffer).order_by(ProductOffer.id.asc()).all()
        buckets: dict[tuple[int, int], list[ProductOffer]] = defaultdict(list)

        for offer in offers:
            if offer.current_price and float(offer.current_price) > 0:
                if offer.lifecycle_status not in {"ARCHIVED", "MISSING"}:
                    if not offer.is_active or offer.is_hidden:
                        offer.is_active = True
                        offer.is_hidden = False
                        offer.lifecycle_status = "ACTIVE"
                        offer.inactive_at = None
                        repaired += 1
            buckets[(int(offer.group_id), int(offer.store_id))].append(offer)

        group_ids: set[int] = set()
        now = datetime.utcnow()

        for (group_id, _store_id), items in buckets.items():
            active = [
                item for item in items
                if item.current_price and float(item.current_price) > 0
                and item.lifecycle_status not in {"MISSING"}
            ]
            if not active:
                continue

            winner = min(
                active,
                key=lambda item: (
                    calculate_offer_total_price(item),
                    -(item.last_checked_at or item.updated_at or item.created_at).timestamp(),
                    item.id,
                ),
            )

            for item in active:
                if item.id == winner.id:
                    item.is_active = True
                    item.is_hidden = False
                    item.lifecycle_status = "ACTIVE"
                    item.inactive_at = None
                else:
                    item.is_active = False
                    item.is_hidden = True
                    item.is_best_offer = False
                    item.lifecycle_status = "ARCHIVED"
                    item.inactive_at = item.inactive_at or now
                    item.admin_note = (
                        "Katalog uzlaştırma: aynı mağazadaki renk/varyant "
                        "tekrarı arşivlendi."
                    )
                    archived += 1
            group_ids.add(group_id)

        for group_id in group_ids:
            update_best_offer(db, group_id)

        db.commit()
        print(f"OK  Aktif durumu onarılan teklif: {repaired}")
        print(f"OK  Arşivlenen aynı-mağaza varyantı: {archived}")
        print(f"OK  Yeniden hesaplanan ürün grubu: {len(group_ids)}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
