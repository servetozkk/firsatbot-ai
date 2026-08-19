from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, delete, func, inspect, select, update

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine
from app.dev.group_merge_safety_analysis_v11_2_3 import main as analysis_main
from app.dev.cross_store_repair_preview_v11_2_1 import main as preview_main

VERSION = "11.2.4"
REPORT_DIR = ROOT / "data" / "reports"
BACKUP_DIR = ROOT / "data" / "backups" / "group_merge"
ANALYSIS_PATH = REPORT_DIR / "v11_2_3_group_merge_safety_analysis.json"
PREVIEW_PATH = REPORT_DIR / "v11_2_1_cross_store_repair_preview.json"
REPORT_PATH = REPORT_DIR / "v11_2_4_specification_merge_execute.json"


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


def comparable_value(row: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (row.get("value_text"), row.get("value_number"), row.get("value_boolean"))


def reference_fields(metadata: MetaData, groups: Table) -> list[tuple[Table, str]]:
    result: list[tuple[Table, str]] = []
    for table_name in inspect(engine).get_table_names():
        table = Table(table_name, metadata, autoload_with=engine)
        for fk in table.foreign_keys:
            if fk.column.table.name == groups.name:
                result.append((table, fk.parent.name))
    return result


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Adayı ve yönü çalışma anında yeniden doğrula.
    analysis_main()
    analysis = json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))
    direction = analysis.get("selected_direction", {})
    source_id = int(direction.get("source_group_id") or 0)
    target_id = int(direction.get("target_group_id") or 0)
    if not source_id or not target_id:
        raise RuntimeError("Kaynak veya hedef grup belirlenemedi.")
    if analysis.get("analysis", {}).get("verdict") != "reference_migration_required":
        raise RuntimeError("Aday artık specification taşıması gerektiren durumda değil; işlem durduruldu.")
    blocking = set(analysis.get("analysis", {}).get("blocking_reference_classes", []))
    if blocking != {"specification"}:
        raise RuntimeError(f"Beklenmeyen referans sınıfı bulundu: {sorted(blocking)}")

    metadata = MetaData()
    groups = Table("product_groups", metadata, autoload_with=engine)
    specs = Table("product_feature_values", metadata, autoload_with=engine)
    refs = reference_fields(metadata, groups)

    with engine.connect() as conn:
        source_group = conn.execute(select(groups).where(groups.c.id == source_id)).mappings().first()
        target_group = conn.execute(select(groups).where(groups.c.id == target_id)).mappings().first()
        if not source_group or not target_group:
            raise RuntimeError("Kaynak veya hedef Product Group bulunamadı.")

        source_specs = [row_dict(r) for r in conn.execute(
            select(specs).where(specs.c.product_group_id == source_id).order_by(specs.c.id)
        ).mappings()]
        target_specs = [row_dict(r) for r in conn.execute(
            select(specs).where(specs.c.product_group_id == target_id).order_by(specs.c.id)
        ).mappings()]

    if not source_specs:
        raise RuntimeError("Kaynak grupta taşınacak specification kaydı bulunamadı.")

    target_by_feature = {int(r["feature_id"]): r for r in target_specs}
    move_rows: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for source_row in source_specs:
        feature_id = int(source_row["feature_id"])
        target_row = target_by_feature.get(feature_id)
        if target_row is None:
            move_rows.append(source_row)
        elif comparable_value(source_row) == comparable_value(target_row):
            duplicate_rows.append({"source": source_row, "target": target_row})
        else:
            conflicts.append({
                "feature_id": feature_id,
                "source": source_row,
                "target": target_row,
                "reason": "aynı feature_id için farklı değer",
            })

    if conflicts:
        conflict_path = REPORT_DIR / "v11_2_4_specification_conflicts.json"
        conflict_path.write_text(json.dumps({
            "version": VERSION,
            "source_group_id": source_id,
            "target_group_id": target_id,
            "conflicts": conflicts,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError(f"Specification çakışması bulundu ({len(conflicts)}). İşlem uygulanmadı. Rapor: {conflict_path}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"v11_2_4_before_merge_{stamp}.json"
    backup = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_group_id": source_id,
        "target_group_id": target_id,
        "source_group": row_dict(source_group),
        "target_group": row_dict(target_group),
        "source_specifications": source_specs,
        "target_specifications_before": target_specs,
        "planned_moves": [int(r["id"]) for r in move_rows],
        "planned_duplicate_deletes": [int(r["source"]["id"]) for r in duplicate_rows],
    }
    backup_path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")

    moved = 0
    duplicates_removed = 0
    source_deleted = False

    # Tek transaction: herhangi bir güvenlik kontrolü başarısızsa tamamı rollback olur.
    with engine.begin() as conn:
        for row in move_rows:
            result = conn.execute(
                update(specs).where(specs.c.id == int(row["id"])).values(product_group_id=target_id)
            )
            if result.rowcount != 1:
                raise RuntimeError(f"Specification taşınamadı: id={row['id']}")
            moved += 1

        for pair in duplicate_rows:
            source_row = pair["source"]
            result = conn.execute(delete(specs).where(specs.c.id == int(source_row["id"])))
            if result.rowcount != 1:
                raise RuntimeError(f"Kopya specification silinemedi: id={source_row['id']}")
            duplicates_removed += 1

        remaining_refs: list[dict[str, Any]] = []
        for table, column in refs:
            count = int(conn.execute(
                select(func.count()).select_from(table).where(table.c[column] == source_id)
            ).scalar_one())
            if count:
                remaining_refs.append({"table": table.name, "column": column, "count": count})
        if remaining_refs:
            raise RuntimeError(f"Kaynak grupta referans kaldı; grup silinmedi: {remaining_refs}")

        result = conn.execute(delete(groups).where(groups.c.id == source_id))
        if result.rowcount != 1:
            raise RuntimeError("Kaynak Product Group silinemedi.")
        source_deleted = True

    # Commit sonrası önizlemeyi yeniden üret.
    preview_main()
    preview = json.loads(PREVIEW_PATH.read_text(encoding="utf-8"))
    remaining_high_moves = len([
        x for x in preview.get("offer_move_candidates", [])
        if x.get("decision") == "high_confidence_move_candidate"
    ])
    remaining_high_merges = len([
        x for x in preview.get("group_merge_candidates", [])
        if x.get("decision") == "high_confidence_merge_candidate"
    ])

    with engine.connect() as conn:
        source_exists = int(conn.execute(
            select(func.count()).select_from(groups).where(groups.c.id == source_id)
        ).scalar_one())
        target_spec_count = int(conn.execute(
            select(func.count()).select_from(specs).where(specs.c.product_group_id == target_id)
        ).scalar_one())

    report = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_group_id": source_id,
        "target_group_id": target_id,
        "source_specification_count_before": len(source_specs),
        "target_specification_count_before": len(target_specs),
        "moved_specifications": moved,
        "duplicate_specifications_removed": duplicates_removed,
        "specification_conflicts": 0,
        "source_group_deleted": source_deleted,
        "source_group_exists_after": bool(source_exists),
        "target_specification_count_after": target_spec_count,
        "remaining_high_confidence_move_candidates": remaining_high_moves,
        "remaining_high_confidence_merge_candidates": remaining_high_merges,
        "backup_path": str(backup_path),
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK  Kaynak grup: {source_id}")
    print(f"OK  Hedef grup: {target_id}")
    print(f"OK  Kaynak specification: {len(source_specs)}")
    print(f"OK  Taşınan specification: {moved}")
    print(f"OK  Aynı değerli kopya kaldırma: {duplicates_removed}")
    print("OK  Specification çakışması: 0")
    print(f"OK  Silinen kaynak grup: {1 if source_deleted else 0}")
    print(f"BİLGİ  Kalan yüksek güvenli taşıma adayı: {remaining_high_moves}")
    print(f"BİLGİ  Kalan yüksek güvenli birleştirme adayı: {remaining_high_merges}")
    print(f"YEDEK: {backup_path}")
    print(f"RAPOR: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
