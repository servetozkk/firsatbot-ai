from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal
from app.database.models import ProductDB, ProductGroup, ProductOffer
from app.models.product import Product
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


def compact_identity(parsed) -> dict:
    return {
        "brand": parsed.brand,
        "family": parsed.family,
        "variant": parsed.variant,
        "ram_gb": parsed.ram_gb,
        "storage_gb": parsed.storage_gb,
        "network": parsed.network,
        "model_code": parsed.model_code,
    }


def main() -> int:
    db = SessionLocal()
    try:
        groups = db.query(ProductGroup).all()
        rows = (
            db.query(ProductOffer, ProductDB, ProductGroup)
            .join(ProductDB, ProductDB.id == ProductOffer.product_id)
            .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
            .all()
        )

        offers_by_group: dict[int, list[tuple]] = defaultdict(list)
        for offer, product, group in rows:
            offers_by_group[group.id].append((offer, product, group))

        empty_groups = []
        duplicate_identity_sources = []
        incompatible_offers = []
        internal_conflicts = []
        identity_map: dict[str, list[int]] = defaultdict(list)

        for group in groups:
            if group.identity_source:
                identity_map[group.identity_source].append(group.id)
            if not offers_by_group.get(group.id):
                empty_groups.append({
                    "group_id": group.id,
                    "canonical_name": group.canonical_name,
                    "identity_source": group.identity_source,
                })

        for identity_source, group_ids in identity_map.items():
            if len(group_ids) > 1:
                duplicate_identity_sources.append({
                    "identity_source": identity_source,
                    "group_ids": group_ids,
                })

        for group_id, items in offers_by_group.items():
            group = items[0][2]
            candidate = OfferMatchingService._group_identity(group)
            seen = {
                "ram_gb": set(),
                "storage_gb": set(),
                "network": set(),
                "variant": set(),
            }

            for offer, row, _group in items:
                product = product_from_row(row)
                parsed = ProductIdentityService.parse(product)
                gate = validate_variant(parsed, candidate)
                if not gate.compatible:
                    incompatible_offers.append({
                        "offer_id": offer.id,
                        "product_id": row.id,
                        "group_id": group_id,
                        "product_name": row.name,
                        "group_identity_source": group.identity_source,
                        "reasons": list(gate.reasons),
                        "parsed": compact_identity(parsed),
                    })

                for key in seen:
                    value = getattr(parsed, key)
                    if value not in (None, ""):
                        seen[key].add(value)

            conflicts = {
                key: sorted(values, key=str)
                for key, values in seen.items()
                if len(values) > 1
            }
            if conflicts:
                internal_conflicts.append({
                    "group_id": group_id,
                    "canonical_name": group.canonical_name,
                    "identity_source": group.identity_source,
                    "offer_count": len(items),
                    "conflicts": conflicts,
                })

        report = {
            "version": "11.1.4",
            "mode": "report_only_no_database_changes",
            "summary": {
                "group_count": len(groups),
                "offer_count": len(rows),
                "empty_group_count": len(empty_groups),
                "duplicate_identity_source_count": len(duplicate_identity_sources),
                "incompatible_offer_count": len(incompatible_offers),
                "internal_conflict_group_count": len(internal_conflicts),
            },
            "empty_groups": empty_groups,
            "duplicate_identity_sources": duplicate_identity_sources,
            "incompatible_offers": incompatible_offers,
            "internal_conflict_groups": internal_conflicts,
        }

        output = ROOT / "data" / "reports" / "v11_1_4_catalog_integrity_audit.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        print(f"OK  Grup sayısı: {len(groups)}")
        print(f"OK  Teklif sayısı: {len(rows)}")
        print(f"UYARI  Boş grup: {len(empty_groups)}")
        print(f"UYARI  Aynı identity_source kullanan grup seti: {len(duplicate_identity_sources)}")
        print(f"UYARI  Grup kimliğiyle uyumsuz teklif: {len(incompatible_offers)}")
        print(f"UYARI  İç varyant çakışması bulunan grup: {len(internal_conflicts)}")
        print(f"RAPOR: {output}")
        print("BİLGİ: Bu denetim veritabanında değişiklik yapmadı.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
