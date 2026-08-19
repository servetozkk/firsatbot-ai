from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine
from app.models.product import Product
from app.services.offer_matching_service import OfferMatchingService
from app.services.product_identity_service import ProductIdentityService

VERSION = "11.2.0"
REPORT_DIR = ROOT / "data" / "reports"


def val(row: Any, key: str, default=None):
    try:
        value = row.get(key, default)
    except AttributeError:
        value = default
    return default if value is None else value


def make_product(row: Any) -> Product:
    return Product(
        name=str(val(row, "name", "")),
        price=float(val(row, "price", 1.0) or 1.0),
        old_price=val(row, "old_price"),
        rating=val(row, "rating"),
        review_count=val(row, "review_count"),
        seller=str(val(row, "seller", "")),
        url=str(val(row, "url", "https://audit.local/product")),
        image=val(row, "image"),
        brand=val(row, "brand"),
        model=val(row, "model"),
        category=val(row, "category"),
        description=val(row, "description"),
        specifications=val(row, "specifications"),
        source_site=val(row, "source_site"),
        product_code=val(row, "product_code"),
    )


def group_proxy(row: Any):
    class G: pass
    g = G()
    for key in ("id", "identity_source", "canonical_name", "brand", "model", "category"):
        setattr(g, key, val(row, key))
    return g


def main() -> int:
    metadata = MetaData()
    groups = Table("product_groups", metadata, autoload_with=engine)
    offers = Table("product_offers", metadata, autoload_with=engine)
    products = Table("products", metadata, autoload_with=engine)
    stores = Table("stores", metadata, autoload_with=engine)

    with engine.connect() as conn:
        group_rows = {r["id"]: r for r in conn.execute(select(groups)).mappings()}
        store_rows = {r["id"]: r for r in conn.execute(select(stores)).mappings()}
        product_rows = {r["id"]: r for r in conn.execute(select(products)).mappings()}
        offer_rows = list(conn.execute(select(offers)).mappings())

    by_group: dict[int, list[Any]] = defaultdict(list)
    store_offer_counts: Counter[str] = Counter()
    active_count = 0
    mismatch: list[dict[str, Any]] = []
    low_score: list[dict[str, Any]] = []

    for offer in offer_rows:
        gid = int(offer["group_id"])
        by_group[gid].append(offer)
        store = store_rows.get(offer["store_id"], {})
        store_name = str(val(store, "name", val(store, "code", f"store:{offer['store_id']}")))
        store_offer_counts[store_name] += 1
        if bool(val(offer, "is_active", True)):
            active_count += 1
        product_row = product_rows.get(offer["product_id"])
        group_row = group_rows.get(gid)
        if not product_row or not group_row:
            mismatch.append({"offer_id": offer["id"], "reason": "ürün veya grup kaydı eksik"})
            continue
        parsed = ProductIdentityService.parse(make_product(product_row))
        candidate = OfferMatchingService._group_identity(group_proxy(group_row))
        score, reasons = OfferMatchingService.score(
            parsed, candidate,
            incoming_category=str(val(product_row, "category", "")),
            candidate_category=str(val(group_row, "category", "")),
        )
        item = {
            "offer_id": offer["id"], "group_id": gid, "product_id": offer["product_id"],
            "store": store_name, "product_name": val(product_row, "name", ""),
            "score": score, "reasons": list(reasons),
            "parsed": {"brand": parsed.brand, "family": parsed.family, "variant": parsed.variant,
                       "ram_gb": parsed.ram_gb, "storage_gb": parsed.storage_gb,
                       "network": parsed.network, "model_code": parsed.model_code},
            "group_identity": val(group_row, "identity_source", ""),
        }
        if score == 0:
            mismatch.append(item)
        elif score < OfferMatchingService.MIN_MATCH_SCORE:
            low_score.append(item)

    multi_store_groups = []
    single_store_groups = []
    store_pairs: Counter[str] = Counter()
    for gid, rows in by_group.items():
        names = sorted({str(val(store_rows.get(r["store_id"], {}), "code", r["store_id"])) for r in rows})
        payload = {"group_id": gid, "canonical_name": val(group_rows.get(gid, {}), "canonical_name", ""),
                   "offer_count": len(rows), "store_count": len(names), "stores": names}
        if len(names) >= 2:
            multi_store_groups.append(payload)
            for i, left in enumerate(names):
                for right in names[i+1:]:
                    store_pairs[f"{left} ↔ {right}"] += 1
        else:
            single_store_groups.append(payload)

    # Olası gereksiz bölünmüş gruplar: aynı marka/kategori içinde matching skoru yüksek iki farklı grup.
    potential_splits = []
    group_list = list(group_rows.values())
    for i, left in enumerate(group_list):
        for right in group_list[i+1:]:
            if val(left, "brand", "") != val(right, "brand", ""):
                continue
            if val(left, "category", "") != val(right, "category", ""):
                continue
            score, reasons = OfferMatchingService.score(
                OfferMatchingService._group_identity(group_proxy(left)),
                OfferMatchingService._group_identity(group_proxy(right)),
                incoming_category=str(val(left, "category", "")),
                candidate_category=str(val(right, "category", "")),
            )
            if score >= OfferMatchingService.MIN_MATCH_SCORE:
                potential_splits.append({"left_group_id": left["id"], "right_group_id": right["id"],
                                         "score": score, "reasons": list(reasons),
                                         "left": val(left, "canonical_name", ""),
                                         "right": val(right, "canonical_name", "")})

    summary = {
        "group_count": len(group_rows), "offer_count": len(offer_rows), "active_offer_count": active_count,
        "store_count": len(store_rows), "multi_store_group_count": len(multi_store_groups),
        "single_store_group_count": len(single_store_groups),
        "cross_store_coverage_percent": round((len(multi_store_groups) / max(1, len(by_group))) * 100, 2),
        "assigned_group_mismatch_count": len(mismatch), "low_score_assignment_count": len(low_score),
        "potential_split_group_pair_count": len(potential_splits),
    }
    report = {
        "version": VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only", "summary": summary,
        "store_offer_counts": dict(store_offer_counts.most_common()),
        "store_pair_overlap": dict(store_pairs.most_common()),
        "assigned_group_mismatches": mismatch,
        "low_score_assignments": low_score,
        "potential_split_groups": potential_splits,
        "multi_store_groups": multi_store_groups,
        "single_store_groups": single_store_groups,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "v11_2_0_cross_store_accuracy_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK  Mağaza sayısı: {summary['store_count']}")
    print(f"OK  Grup sayısı: {summary['group_count']}")
    print(f"OK  Teklif sayısı: {summary['offer_count']}")
    print(f"OK  Aktif teklif: {summary['active_offer_count']}")
    print(f"OK  Çok mağazalı grup: {summary['multi_store_group_count']}")
    print(f"BİLGİ  Cross-store kapsama: %{summary['cross_store_coverage_percent']}")
    print(f"UYARI  Atandığı grupla uyumsuz teklif: {summary['assigned_group_mismatch_count']}")
    print(f"UYARI  Düşük skorlu atama: {summary['low_score_assignment_count']}")
    print(f"UYARI  Olası bölünmüş grup çifti: {summary['potential_split_group_pair_count']}")
    print(f"RAPOR: {path}")
    print("BİLGİ: Denetim veritabanında değişiklik yapmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
