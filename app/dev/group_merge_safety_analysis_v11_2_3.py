from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, func, inspect, select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine
from app.dev.cross_store_repair_preview_v11_2_1 import main as preview_main

VERSION = "11.2.3"
REPORT_DIR = ROOT / "data" / "reports"
PREVIEW_PATH = REPORT_DIR / "v11_2_1_cross_store_repair_preview.json"
REPORT_PATH = REPORT_DIR / "v11_2_3_group_merge_safety_analysis.json"


def serial(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    return value


def row_dict(row: Any) -> dict[str, Any]:
    return {str(k): serial(v) for k, v in dict(row).items()}


def classify_reference(table_name: str) -> str:
    name = table_name.casefold()
    if "offer" in name:
        return "offer"
    if "price" in name or "history" in name:
        return "price_history"
    if "favorite" in name or "favourite" in name:
        return "favorite"
    if "alarm" in name or "alert" in name:
        return "alarm"
    if "image" in name or "gallery" in name:
        return "image"
    if "spec" in name or "feature" in name or "attribute" in name:
        return "specification"
    if "compare" in name:
        return "comparison"
    return "other"


def reference_fields(metadata: MetaData, group_table: Table) -> list[tuple[Table, str]]:
    refs: list[tuple[Table, str]] = []
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        table = Table(table_name, metadata, autoload_with=engine)
        for fk in table.foreign_keys:
            if fk.column.table.name == group_table.name:
                refs.append((table, fk.parent.name))
    return refs


def table_reference_detail(conn, table: Table, column: str, group_id: int) -> dict[str, Any]:
    count = int(conn.execute(select(func.count()).select_from(table).where(table.c[column] == group_id)).scalar_one())
    samples: list[dict[str, Any]] = []
    if count:
        samples = [row_dict(r) for r in conn.execute(select(table).where(table.c[column] == group_id).limit(3)).mappings()]
    return {
        "table": table.name,
        "column": column,
        "classification": classify_reference(table.name),
        "count": count,
        "samples": samples,
    }


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    preview_main()
    preview = json.loads(PREVIEW_PATH.read_text(encoding="utf-8"))
    candidates = [
        item for item in preview.get("group_merge_candidates", [])
        if item.get("decision") == "high_confidence_merge_candidate"
    ]

    if not candidates:
        raise RuntimeError("Yüksek güvenli grup birleştirme adayı bulunamadı.")
    if len(candidates) > 1:
        raise RuntimeError(f"Güvenlik durdurması: {len(candidates)} yüksek güvenli aday bulundu.")

    candidate = candidates[0]
    left_id = int(candidate["left_group_id"])
    right_id = int(candidate["right_group_id"])

    metadata = MetaData()
    groups = Table("product_groups", metadata, autoload_with=engine)
    offers = Table("product_offers", metadata, autoload_with=engine)
    refs = reference_fields(metadata, groups)

    with engine.connect() as conn:
        group_rows = {
            int(r["id"]): row_dict(r)
            for r in conn.execute(select(groups).where(groups.c.id.in_([left_id, right_id]))).mappings()
        }
        if len(group_rows) != 2:
            raise RuntimeError("Aday gruplardan biri veritabanında bulunamadı.")

        offer_counts = {
            gid: int(conn.execute(select(func.count()).select_from(offers).where(offers.c.group_id == gid)).scalar_one())
            for gid in (left_id, right_id)
        }
        target_id, source_id = (
            (left_id, right_id)
            if (offer_counts[left_id], -left_id) >= (offer_counts[right_id], -right_id)
            else (right_id, left_id)
        )

        references: dict[str, list[dict[str, Any]]] = {str(left_id): [], str(right_id): []}
        for gid in (left_id, right_id):
            for table, column in refs:
                references[str(gid)].append(table_reference_detail(conn, table, column, gid))

    source_non_offer = [
        r for r in references[str(source_id)]
        if r["count"] and r["classification"] != "offer"
    ]
    target_non_offer = [
        r for r in references[str(target_id)]
        if r["count"] and r["classification"] != "offer"
    ]
    blocking_classes = sorted({r["classification"] for r in source_non_offer + target_non_offer})
    unknown_refs = [r for r in source_non_offer + target_non_offer if r["classification"] == "other"]

    # Otomatik birleştirme ancak iki tarafta da teklif dışı referans yoksa güvenlidir.
    if not source_non_offer and not target_non_offer:
        verdict = "safe_for_automatic_merge"
        recommendation = "Teklifleri hedef gruba taşı, kaynak grubu sil ve ardından bütünlük denetimi çalıştır."
    elif unknown_refs:
        verdict = "manual_schema_review_required"
        recommendation = "Bilinmeyen referans tabloları bulundu. Tablo bazlı taşıma ve benzersizlik kuralları incelenmeden birleştirme yapılmamalı."
    else:
        verdict = "reference_migration_required"
        recommendation = "İlişkili kayıtlar hedef gruba tablo bazlı taşınmalı veya birleştirilmeli; çakışma kontrolü ve rollback zorunlu."

    migration_plan: list[dict[str, Any]] = []
    for ref in source_non_offer:
        migration_plan.append({
            "table": ref["table"],
            "column": ref["column"],
            "classification": ref["classification"],
            "source_count": ref["count"],
            "action": "target_group_id ile güncellemeden önce hedefte eşdeğer/benzersiz kayıt çakışmasını kontrol et",
        })

    report = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_dry_run",
        "candidate": candidate,
        "selected_direction": {
            "source_group_id": source_id,
            "target_group_id": target_id,
            "selection_reason": "daha fazla teklif taşıyan grup hedef; eşitse düşük grup kimliği hedef",
            "source_offer_count": offer_counts[source_id],
            "target_offer_count": offer_counts[target_id],
        },
        "groups": group_rows,
        "references": references,
        "analysis": {
            "source_non_offer_reference_count": sum(r["count"] for r in source_non_offer),
            "target_non_offer_reference_count": sum(r["count"] for r in target_non_offer),
            "blocking_reference_classes": blocking_classes,
            "unknown_reference_table_count": len(unknown_refs),
            "verdict": verdict,
            "recommendation": recommendation,
        },
        "migration_plan": migration_plan,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK  Aday grup çifti: {left_id} <-> {right_id}")
    print(f"BİLGİ  Kaynak grup: {source_id} (teklif={offer_counts[source_id]})")
    print(f"BİLGİ  Hedef grup: {target_id} (teklif={offer_counts[target_id]})")
    print(f"UYARI  Kaynak teklif dışı referans: {report['analysis']['source_non_offer_reference_count']}")
    print(f"UYARI  Hedef teklif dışı referans: {report['analysis']['target_non_offer_reference_count']}")
    print(f"BİLGİ  Engel sınıfları: {', '.join(blocking_classes) if blocking_classes else 'yok'}")
    print(f"KARAR: {verdict}")
    print(f"RAPOR: {REPORT_PATH}")
    print("BİLGİ: Analiz veritabanında değişiklik yapmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
