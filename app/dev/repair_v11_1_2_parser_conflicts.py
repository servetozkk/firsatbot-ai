from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal
from app.database.models import ProductDB, ProductGroup, ProductOffer
from app.models.product import Product
from app.services.multi_store_service import ensure_product_group
from app.services.offer_integrity_service import validate_variant
from app.services.offer_matching_service import OfferMatchingService
from app.services.product_identity_service import ProductIdentityService


def product_from_row(row: ProductDB) -> Product:
    try:
        specifications = json.loads(row.specifications or "{}")
    except (TypeError, json.JSONDecodeError):
        specifications = {}

    return Product(
        name=row.name,
        price=float(row.price or 0),
        old_price=row.old_price,
        rating=row.rating,
        review_count=row.review_count,
        seller=row.seller or "",
        url=row.url,
        image=row.image,
        brand=row.brand,
        model=row.model,
        category=row.category,
        description=row.description,
        specifications=specifications,
        stock_status=row.stock_status,
        product_code=row.product_code,
    )


def main() -> int:
    db = SessionLocal()
    changes = []
    checked = 0
    try:
        rows = (
            db.query(ProductOffer, ProductDB, ProductGroup)
            .join(ProductDB, ProductDB.id == ProductOffer.product_id)
            .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
            .all()
        )

        for offer, product_row, current_group in rows:
            checked += 1
            product = product_from_row(product_row)
            incoming = ProductIdentityService.parse(product)
            candidate = OfferMatchingService._group_identity(current_group)
            gate = validate_variant(incoming, candidate)
            if gate.compatible:
                continue

            target_group = ensure_product_group(db, product)
            if target_group.id == current_group.id:
                offer.is_active = False
                offer.inactive_at = datetime.utcnow()
                offer.lifecycle_status = "ARCHIVED"
                offer.match_reason = (
                    "V11.1.2 parser ve varyant karantinası: "
                    + "; ".join(gate.reasons)
                )
                changes.append({
                    "offer_id": offer.id,
                    "product_id": product_row.id,
                    "action": "quarantined",
                    "from_group": current_group.id,
                    "reason": list(gate.reasons),
                    "parsed": ProductIdentityService.explain(product),
                })
                continue

            old_group_id = current_group.id
            offer.group_id = target_group.id
            offer.match_score = 100.0
            offer.match_reason = (
                "V11.1.2 parser ve varyant onarımı: "
                + "; ".join(gate.reasons)
            )
            offer.is_active = True
            offer.inactive_at = None
            offer.lifecycle_status = "ACTIVE"
            changes.append({
                "offer_id": offer.id,
                "product_id": product_row.id,
                "action": "moved",
                "from_group": old_group_id,
                "to_group": target_group.id,
                "reason": list(gate.reasons),
                "parsed": ProductIdentityService.explain(product),
            })

        db.commit()
        output = ROOT / "data" / "reports" / "v11_1_2_parser_repair.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "checked_offer_count": checked,
                    "repaired_or_quarantined": len(changes),
                    "items": changes,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        print(f"OK  Etkilenen teklif kontrolü: {checked}")
        print(f"OK  Taşınan/doğrulanan: {len(changes)}")
        print(f"RAPOR: {output}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
