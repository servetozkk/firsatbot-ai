from __future__ import annotations

import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from app.database.database import SessionLocal
from app.database.models import ProductGroup
from app.services.comparison_service import get_product_comparison
from app.services.product_similarity_service import category_family
from app.services.smart_recommendation_service import get_smart_recommendations

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "products.db"
REPORT_PATH = ROOT / "data" / "reports" / "v13_2_3_recommendation_real_data_acceptance.json"


def check(value: bool, message: str, checks: list[dict[str, Any]]) -> None:
    row = {"ok": bool(value), "message": message}
    checks.append(row)
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    checks: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []

    check(version == "13.2.3", "VERSION 13.2.3", checks)

    with sqlite3.connect(DB_PATH) as conn:
        check(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity_check başarılı", checks)
        check(not conn.execute("PRAGMA foreign_key_check").fetchall(), "foreign key ihlali yok", checks)

    db = SessionLocal()
    analyzed_groups = 0
    groups_with_recommendations = 0
    total_items = 0
    unique_pairs: set[tuple[int, str]] = set()
    category_safe = 0
    cheaper_verified = 0
    upgrade_verified = 0
    critical_variant_caps = 0
    low_confidence_items = 0
    multi_store_items = 0
    try:
        groups = db.query(ProductGroup).order_by(ProductGroup.id.asc()).all()
        for current in groups:
            comparison = get_product_comparison(db=db, identity_key=current.group_key)
            if not comparison or _number(comparison.get("best_price")) <= 0:
                continue
            analyzed_groups += 1
            current_price = _number(comparison.get("best_price"))
            buckets = get_smart_recommendations(
                db=db,
                current_group=current,
                current_comparison=comparison,
                per_bucket=6,
            )
            bucket_count = sum(len(items) for items in buckets.values())
            if bucket_count:
                groups_with_recommendations += 1

            for bucket, items in buckets.items():
                seen: set[str] = set()
                for item in items:
                    total_items += 1
                    identity_key = str(item.get("identity_key") or "")
                    check(bool(identity_key), f"alternatif ürün kimliği mevcut (grup {current.id})", checks)
                    check(identity_key != current.group_key, f"ürün kendisini önermiyor (grup {current.id})", checks)
                    check(identity_key not in seen, f"aynı kutuda kopya alternatif yok (grup {current.id}, {bucket})", checks)
                    seen.add(identity_key)

                    candidate = db.query(ProductGroup).filter(ProductGroup.group_key == identity_key).first()
                    check(candidate is not None, f"alternatif global katalogda mevcut ({identity_key})", checks)
                    check(
                        category_family(current.category) == category_family(candidate.category),
                        f"alternatif aynı kategori ailesinde ({current.id} -> {candidate.id})",
                        checks,
                    )
                    category_safe += 1

                    score = _number(item.get("recommendation_score"), -1)
                    similarity = _number(item.get("similarity_score"), -1)
                    confidence = _number(item.get("deal_confidence"), -1)
                    difference = _number(item.get("price_difference_percent"))
                    best_price = _number(item.get("best_price"))
                    components = item.get("similarity_components") or {}

                    check(0 <= score <= 100, f"öneri puanı 0-100 aralığında ({identity_key})", checks)
                    check(0 <= similarity <= 100, f"teknik benzerlik 0-100 aralığında ({identity_key})", checks)
                    check(best_price > 0, f"alternatifin geçerli fiyatı var ({identity_key})", checks)
                    check(
                        item.get("compare_url") == f"/karsilastir/compare?left={current.group_key}&right={identity_key}",
                        f"karşılaştırma bağlantısı doğru ({identity_key})",
                        checks,
                    )
                    check(bool(item.get("comparison_highlights")), f"teknik/fiyat fark özeti mevcut ({identity_key})", checks)
                    check(bool(item.get("recommendation_reason")), f"öneri nedeni açıklanabilir ({identity_key})", checks)

                    if bucket == "cheaper":
                        check(best_price < current_price * 0.97, f"daha ucuz etiketi gerçek fiyatla uyumlu ({identity_key})", checks)
                        cheaper_verified += 1
                    if bucket == "upgrade":
                        check(
                            current_price * 1.03 <= best_price <= current_price * 1.35,
                            f"bir üst seviye fiyat aralığı doğru ({identity_key})",
                            checks,
                        )
                        upgrade_verified += 1

                    if item.get("recommendation_code") == "cheaper_same_performance":
                        check(difference <= -3 and similarity >= 60, f"aynı performans daha ucuz sınıfı tutarlı ({identity_key})", checks)
                    if confidence < 35 or similarity < 45:
                        check(item.get("recommendation_code") == "insufficient_data", f"düşük güvenli öneri kesin konuşmuyor ({identity_key})", checks)
                        low_confidence_items += 1

                    network = _number(components.get("network"), -1)
                    gpu = _number(components.get("gpu"), -1)
                    ram = _number(components.get("ram"), -1)
                    storage = _number(components.get("storage"), -1)
                    if network == 0 or gpu == 0:
                        check(similarity <= 64, f"kritik network/GPU farkı puanı sınırlandırıyor ({identity_key})", checks)
                        critical_variant_caps += 1
                    if (0 <= ram < 25) or (0 <= storage < 25):
                        check(similarity <= 69, f"kritik RAM/depolama farkı puanı sınırlandırıyor ({identity_key})", checks)
                        critical_variant_caps += 1

                    if int(item.get("offer_count", 0) or 0) >= 2:
                        multi_store_items += 1
                    unique_pairs.add((current.id, identity_key))
                    if len(samples) < 30:
                        samples.append({
                            "source_group_id": current.id,
                            "source_identity_key": current.group_key,
                            "bucket": bucket,
                            "candidate_identity_key": identity_key,
                            "candidate_group_id": candidate.id,
                            "recommendation_score": score,
                            "similarity_score": similarity,
                            "price_difference_percent": difference,
                            "recommendation_label": item.get("recommendation_label"),
                            "offer_count": item.get("offer_count"),
                        })
    finally:
        db.close()

    check(analyzed_groups > 0, f"gerçek fiyatı olan ürünler analiz edildi: {analyzed_groups}", checks)
    check(groups_with_recommendations > 0, f"gerçek veride alternatif üreten ürün bulundu: {groups_with_recommendations}", checks)
    check(total_items > 0, f"gerçek alternatif önerileri doğrulandı: {total_items}", checks)
    check(category_safe == total_items, "tüm öneriler kategori güvenli", checks)
    check(len(unique_pairs) > 0, f"benzersiz ürün çiftleri doğrulandı: {len(unique_pairs)}", checks)

    report = {
        "version": version,
        "generated_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "status": "RECOMMENDATION_REAL_DATA_ACCEPTANCE_READY",
        "summary": {
            "analyzed_product_groups": analyzed_groups,
            "groups_with_recommendations": groups_with_recommendations,
            "recommendation_items_checked": total_items,
            "unique_product_pairs": len(unique_pairs),
            "category_safe_items": category_safe,
            "cheaper_labels_verified": cheaper_verified,
            "upgrade_labels_verified": upgrade_verified,
            "critical_variant_caps_verified": critical_variant_caps,
            "low_confidence_items_verified": low_confidence_items,
            "multi_store_recommendations": multi_store_items,
            "checks_passed": sum(1 for row in checks if row["ok"]),
            "checks_total": len(checks),
        },
        "samples": samples,
        "checks": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RAPOR: {REPORT_PATH}")
    print("DURUM: RECOMMENDATION_REAL_DATA_ACCEPTANCE_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
