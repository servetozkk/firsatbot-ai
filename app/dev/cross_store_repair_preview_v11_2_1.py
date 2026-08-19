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
from app.services.product_identity_service import ProductIdentityService, ParsedProductIdentity

VERSION = "11.2.1"
REPORT_DIR = ROOT / "data" / "reports"
HIGH_CONFIDENCE_SCORE = max(95.0, OfferMatchingService.HIGH_CONFIDENCE_SCORE)
MIN_MARGIN = OfferMatchingService.AMBIGUITY_MARGIN


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
        url=str(val(row, "url", "https://preview.local/product")),
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
    class G:
        pass
    group = G()
    for key in ("id", "identity_source", "canonical_name", "brand", "model", "category"):
        setattr(group, key, val(row, key))
    return group


def identity_dict(identity: ParsedProductIdentity) -> dict[str, Any]:
    return {
        "brand": identity.brand,
        "family": identity.family,
        "variant": identity.variant,
        "ram_gb": identity.ram_gb,
        "storage_gb": identity.storage_gb,
        "network": identity.network,
        "screen_inch": identity.screen_inch,
        "model_code": identity.model_code,
        "product_code": identity.product_code,
    }


def difference_summary(left: ParsedProductIdentity, right: ParsedProductIdentity) -> list[str]:
    differences: list[str] = []
    for label, a, b in (
        ("brand", left.brand, right.brand),
        ("family", left.family, right.family),
        ("variant", left.variant, right.variant),
        ("ram_gb", left.ram_gb, right.ram_gb),
        ("storage_gb", left.storage_gb, right.storage_gb),
        ("network", left.network, right.network),
        ("model_code", left.model_code, right.model_code),
        ("product_code", left.product_code, right.product_code),
    ):
        if a != b and (a not in (None, "") or b not in (None, "")):
            differences.append(f"{label}: {a!r} -> {b!r}")
    return differences


def classify_zero_score(reasons: tuple[str, ...]) -> str:
    text = " ".join(reasons).casefold()
    if "ram" in text:
        return "ram_conflict"
    if "depolama" in text:
        return "storage_conflict"
    if "şebeke" in text or "sebeke" in text:
        return "network_conflict"
    if "model kodu" in text:
        return "model_code_conflict"
    if "marka" in text:
        return "brand_conflict"
    if "kategori" in text:
        return "category_conflict"
    if "varyant" in text:
        return "variant_conflict"
    if "ailesi" in text:
        return "family_mismatch"
    return "other_incompatibility"


def main() -> int:
    metadata = MetaData()
    groups_table = Table("product_groups", metadata, autoload_with=engine)
    offers_table = Table("product_offers", metadata, autoload_with=engine)
    products_table = Table("products", metadata, autoload_with=engine)
    stores_table = Table("stores", metadata, autoload_with=engine)

    with engine.connect() as conn:
        groups = {int(r["id"]): r for r in conn.execute(select(groups_table)).mappings()}
        offers = list(conn.execute(select(offers_table)).mappings())
        products = {int(r["id"]): r for r in conn.execute(select(products_table)).mappings()}
        stores = {int(r["id"]): r for r in conn.execute(select(stores_table)).mappings()}

    group_identities = {
        gid: OfferMatchingService._group_identity(group_proxy(row))
        for gid, row in groups.items()
    }
    groups_by_brand_category: dict[tuple[str, str], list[int]] = defaultdict(list)
    for gid, row in groups.items():
        brand = str(val(row, "brand", "") or "")
        category = str(val(row, "category", "") or "")
        groups_by_brand_category[(brand, category)].append(gid)

    assigned_mismatches: list[dict[str, Any]] = []
    low_score_assignments: list[dict[str, Any]] = []
    high_confidence_moves: list[dict[str, Any]] = []
    ambiguous_moves: list[dict[str, Any]] = []
    no_safe_target: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()

    for offer in offers:
        offer_id = int(offer["id"])
        current_gid = int(offer["group_id"])
        product_row = products.get(int(offer["product_id"]))
        current_group = groups.get(current_gid)
        if product_row is None or current_group is None:
            assigned_mismatches.append({
                "offer_id": offer_id,
                "current_group_id": current_gid,
                "decision": "broken_reference",
                "reason": "ürün veya grup kaydı eksik",
            })
            reason_counts["broken_reference"] += 1
            continue

        product = make_product(product_row)
        incoming = ProductIdentityService.parse(product)
        current_identity = group_identities[current_gid]
        current_score, current_reasons = OfferMatchingService.score(
            incoming,
            current_identity,
            incoming_category=str(val(product_row, "category", "")),
            candidate_category=str(val(current_group, "category", "")),
        )

        base = {
            "offer_id": offer_id,
            "product_id": int(offer["product_id"]),
            "store_id": int(offer["store_id"]),
            "store": str(val(stores.get(int(offer["store_id"]), {}), "name", val(stores.get(int(offer["store_id"]), {}), "code", offer["store_id"]))),
            "product_name": str(val(product_row, "name", "")),
            "current_group_id": current_gid,
            "current_group_name": str(val(current_group, "canonical_name", "")),
            "current_score": current_score,
            "current_reasons": list(current_reasons),
            "parsed_identity": identity_dict(incoming),
            "current_group_identity": identity_dict(current_identity),
            "current_identity_source": str(val(current_group, "identity_source", "")),
        }

        if current_score == 0:
            category = classify_zero_score(current_reasons)
            reason_counts[category] += 1
            assigned_mismatches.append({**base, "classification": category})
        elif current_score < OfferMatchingService.MIN_MATCH_SCORE:
            reason_counts["low_score"] += 1
            low_score_assignments.append({**base, "classification": "low_score"})
        else:
            continue

        candidate_ids = groups_by_brand_category.get((incoming.brand, str(val(product_row, "category", "") or "")), [])
        if not candidate_ids:
            candidate_ids = [gid for gid, ident in group_identities.items() if ident.brand == incoming.brand]

        ranked: list[tuple[int, float, tuple[str, ...]]] = []
        for gid in candidate_ids:
            if gid == current_gid:
                continue
            row = groups[gid]
            score, reasons = OfferMatchingService.score(
                incoming,
                group_identities[gid],
                incoming_category=str(val(product_row, "category", "")),
                candidate_category=str(val(row, "category", "")),
            )
            if score > 0:
                ranked.append((gid, score, reasons))
        ranked.sort(key=lambda item: item[1], reverse=True)

        if not ranked:
            no_safe_target.append({**base, "decision": "no_compatible_group"})
            continue

        best_gid, best_score, best_reasons = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = round(best_score - second_score, 2)
        best_group = groups[best_gid]
        proposal = {
            **base,
            "suggested_group_id": best_gid,
            "suggested_group_name": str(val(best_group, "canonical_name", "")),
            "suggested_identity_source": str(val(best_group, "identity_source", "")),
            "suggested_group_identity": identity_dict(group_identities[best_gid]),
            "suggested_score": best_score,
            "suggested_reasons": list(best_reasons),
            "second_best_score": second_score,
            "score_margin": margin,
            "identity_differences": difference_summary(current_identity, group_identities[best_gid]),
        }
        if best_score >= HIGH_CONFIDENCE_SCORE and margin >= MIN_MARGIN:
            high_confidence_moves.append({**proposal, "decision": "high_confidence_move_candidate"})
        else:
            ambiguous_moves.append({**proposal, "decision": "manual_review_required"})

    # Bölünmüş grup adaylarını, varyant güvenlik kuralları ve teklif mağazalarıyla birlikte sınıflandır.
    offers_by_group: dict[int, list[Any]] = defaultdict(list)
    for offer in offers:
        offers_by_group[int(offer["group_id"])].append(offer)

    merge_candidates: list[dict[str, Any]] = []
    rejected_group_pairs: list[dict[str, Any]] = []
    group_list = list(groups.items())
    for idx, (left_gid, left_row) in enumerate(group_list):
        left_identity = group_identities[left_gid]
        for right_gid, right_row in group_list[idx + 1:]:
            if str(val(left_row, "brand", "")) != str(val(right_row, "brand", "")):
                continue
            if str(val(left_row, "category", "")) != str(val(right_row, "category", "")):
                continue
            right_identity = group_identities[right_gid]
            score, reasons = OfferMatchingService.score(
                left_identity,
                right_identity,
                incoming_category=str(val(left_row, "category", "")),
                candidate_category=str(val(right_row, "category", "")),
            )
            if score == 0:
                conflict = classify_zero_score(reasons)
                if conflict in {"ram_conflict", "storage_conflict", "network_conflict", "model_code_conflict", "variant_conflict"}:
                    rejected_group_pairs.append({
                        "left_group_id": left_gid,
                        "right_group_id": right_gid,
                        "left": str(val(left_row, "canonical_name", "")),
                        "right": str(val(right_row, "canonical_name", "")),
                        "decision": "must_not_merge",
                        "classification": conflict,
                        "reasons": list(reasons),
                    })
                continue
            if score < OfferMatchingService.MIN_MATCH_SCORE:
                continue
            left_stores = sorted({int(o["store_id"]) for o in offers_by_group.get(left_gid, [])})
            right_stores = sorted({int(o["store_id"]) for o in offers_by_group.get(right_gid, [])})
            item = {
                "left_group_id": left_gid,
                "right_group_id": right_gid,
                "left": str(val(left_row, "canonical_name", "")),
                "right": str(val(right_row, "canonical_name", "")),
                "score": score,
                "reasons": list(reasons),
                "left_offer_count": len(offers_by_group.get(left_gid, [])),
                "right_offer_count": len(offers_by_group.get(right_gid, [])),
                "left_store_ids": left_stores,
                "right_store_ids": right_stores,
                "cross_store_opportunity": bool(set(left_stores) != set(right_stores)),
                "identity_differences": difference_summary(left_identity, right_identity),
                "decision": "high_confidence_merge_candidate" if score >= HIGH_CONFIDENCE_SCORE else "manual_merge_review",
            }
            merge_candidates.append(item)

    summary = {
        "group_count": len(groups),
        "offer_count": len(offers),
        "assigned_group_mismatch_count": len(assigned_mismatches),
        "low_score_assignment_count": len(low_score_assignments),
        "high_confidence_move_candidate_count": len(high_confidence_moves),
        "manual_move_review_count": len(ambiguous_moves),
        "no_safe_target_count": len(no_safe_target),
        "potential_merge_pair_count": len(merge_candidates),
        "high_confidence_merge_candidate_count": sum(1 for item in merge_candidates if item["decision"] == "high_confidence_merge_candidate"),
        "manual_merge_review_count": sum(1 for item in merge_candidates if item["decision"] == "manual_merge_review"),
        "must_not_merge_pair_count": len(rejected_group_pairs),
    }
    report = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_preview",
        "thresholds": {
            "minimum_match_score": OfferMatchingService.MIN_MATCH_SCORE,
            "high_confidence_score": HIGH_CONFIDENCE_SCORE,
            "minimum_margin": MIN_MARGIN,
        },
        "summary": summary,
        "classification_counts": dict(reason_counts.most_common()),
        "high_confidence_move_candidates": high_confidence_moves,
        "manual_move_review": ambiguous_moves,
        "no_safe_target": no_safe_target,
        "assigned_group_mismatches": assigned_mismatches,
        "low_score_assignments": low_score_assignments,
        "group_merge_candidates": sorted(merge_candidates, key=lambda item: item["score"], reverse=True),
        "must_not_merge_group_pairs": rejected_group_pairs,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "v11_2_1_cross_store_repair_preview.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK  Grup sayısı: {summary['group_count']}")
    print(f"OK  Teklif sayısı: {summary['offer_count']}")
    print(f"UYARI  Uyumsuz atama: {summary['assigned_group_mismatch_count']}")
    print(f"UYARI  Düşük skorlu atama: {summary['low_score_assignment_count']}")
    print(f"BİLGİ  Yüksek güvenli taşıma adayı: {summary['high_confidence_move_candidate_count']}")
    print(f"BİLGİ  Manuel taşıma incelemesi: {summary['manual_move_review_count']}")
    print(f"BİLGİ  Güvenli hedef bulunamayan: {summary['no_safe_target_count']}")
    print(f"BİLGİ  Yüksek güvenli grup birleştirme adayı: {summary['high_confidence_merge_candidate_count']}")
    print(f"BİLGİ  Manuel grup birleştirme incelemesi: {summary['manual_merge_review_count']}")
    print(f"OK  Birleştirilmemesi gereken varyant çifti: {summary['must_not_merge_pair_count']}")
    print(f"RAPOR: {report_path}")
    print("BİLGİ: Önizleme veritabanında değişiklik yapmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
