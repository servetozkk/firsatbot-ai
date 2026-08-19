from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.database.database import SessionLocal
from app.database.models import ProductDB, ProductGroup, ProductOffer
from app.models.product import Product
from app.services.offer_matching_service import OfferMatchingService


def as_product(row: ProductDB) -> Product:
    return Product(
        name=row.name,
        price=row.price,
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
        product_code=getattr(row, "product_code", None),
    )


def run(limit: int, output: Path) -> None:
    db = SessionLocal()
    try:
        rows = (
            db.query(ProductDB, ProductOffer)
            .outerjoin(ProductOffer, ProductOffer.product_id == ProductDB.id)
            .order_by(ProductDB.id.asc())
            .limit(limit)
            .all()
        )
        groups = db.query(ProductGroup).all()
        report = []
        counters = Counter()

        for product_row, offer in rows:
            product = as_product(product_row)
            decision = OfferMatchingService.find_best_group(db, product, groups=groups)
            current_group_id = offer.group_id if offer else None
            suggested_group_id = decision.group.id if decision.group else None
            status = "same" if current_group_id and current_group_id == suggested_group_id else (
                "suggested_change" if decision.matched else decision.confidence
            )
            counters[status] += 1
            report.append({
                "product_id": product_row.id,
                "name": product_row.name,
                "current_group_id": current_group_id,
                "suggested_group_id": suggested_group_id,
                "score": decision.score,
                "second_score": decision.second_score,
                "confidence": decision.confidence,
                "ambiguous": decision.ambiguous,
                "status": status,
                "reasons": list(decision.reasons),
            })

        payload = {"summary": dict(counters), "items": report}
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("AI ürün eşleştirme denetimi tamamlandı.")
        print("Özet:", dict(counters))
        print("Rapor:", output.resolve())
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ürün gruplarını güvenli biçimde denetler; veritabanını değiştirmez.")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--output", default="ai_product_matching_report.json")
    args = parser.parse_args()
    run(args.limit, Path(args.output))
