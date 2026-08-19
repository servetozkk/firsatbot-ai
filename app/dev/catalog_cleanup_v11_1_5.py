from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, delete, inspect, select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine

VERSION = "11.1.5"
REPORT_DIR = ROOT / "data" / "reports"
BACKUP_DIR = ROOT / "data" / "backups" / "catalog_cleanup"


def json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def discover_references() -> list[dict[str, str]]:
    inspector = inspect(engine)
    refs: list[dict[str, str]] = []
    for table_name in inspector.get_table_names():
        if table_name == "product_groups":
            continue
        for fk in inspector.get_foreign_keys(table_name):
            if fk.get("referred_table") != "product_groups":
                continue
            local = fk.get("constrained_columns") or []
            remote = fk.get("referred_columns") or []
            for local_col, remote_col in zip(local, remote):
                if remote_col == "id":
                    refs.append({"table": table_name, "column": local_col})
    return sorted(refs, key=lambda item: (item["table"], item["column"]))


def build_analysis() -> dict[str, Any]:
    metadata = MetaData()
    groups = Table("product_groups", metadata, autoload_with=engine)
    refs = discover_references()
    ref_tables: dict[str, Table] = {}
    for ref in refs:
        ref_tables.setdefault(ref["table"], Table(ref["table"], metadata, autoload_with=engine))

    items: list[dict[str, Any]] = []
    with engine.connect() as conn:
        group_rows = conn.execute(select(groups).order_by(groups.c.id)).mappings().all()
        for row in group_rows:
            counts: dict[str, int] = {}
            total = 0
            for ref in refs:
                table = ref_tables[ref["table"]]
                count = conn.execute(
                    select(table.c[ref["column"]]).where(table.c[ref["column"]] == row["id"])
                ).all()
                value = len(count)
                counts[f'{ref["table"]}.{ref["column"]}'] = value
                total += value
            items.append({
                "group": {key: json_value(value) for key, value in row.items()},
                "reference_counts": counts,
                "total_references": total,
                "classification": "safe_to_delete" if total == 0 else "protected",
            })

    safe = [item for item in items if item["classification"] == "safe_to_delete"]
    protected = [item for item in items if item["classification"] == "protected"]
    return {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_columns": refs,
        "summary": {
            "group_count": len(items),
            "safe_to_delete_count": len(safe),
            "protected_count": len(protected),
        },
        "safe_to_delete": safe,
        "protected": protected,
    }


def write_report(analysis: dict[str, Any], mode: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"v11_1_5_catalog_cleanup_{mode}.json"
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def backup_candidates(analysis: dict[str, Any]) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"product_groups_before_cleanup_{stamp}.json"
    payload = {
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "groups": [item["group"] for item in analysis["safe_to_delete"]],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def execute_cleanup(analysis: dict[str, Any]) -> tuple[int, Path]:
    backup = backup_candidates(analysis)
    ids = [item["group"]["id"] for item in analysis["safe_to_delete"]]
    if not ids:
        return 0, backup
    metadata = MetaData()
    groups = Table("product_groups", metadata, autoload_with=engine)
    with engine.begin() as conn:
        result = conn.execute(delete(groups).where(groups.c.id.in_(ids)))
    return int(result.rowcount or 0), backup


def restore_backup(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("groups") or []
    metadata = MetaData()
    groups = Table("product_groups", metadata, autoload_with=engine)
    restored = 0
    with engine.begin() as conn:
        for row in rows:
            exists = conn.execute(select(groups.c.id).where(groups.c.id == row["id"])).first()
            if exists:
                continue
            allowed = {column.name for column in groups.columns}
            clean = {key: value for key, value in row.items() if key in allowed}
            conn.execute(groups.insert().values(**clean))
            restored += 1
    return restored


def main() -> int:
    parser = argparse.ArgumentParser(description="FırsatAI v11.1.5 güvenli katalog temizliği")
    parser.add_argument("--execute", action="store_true", help="Sadece sıfır referanslı grupları sil")
    parser.add_argument("--restore", type=Path, help="JSON yedeğini geri yükle")
    args = parser.parse_args()

    if args.restore:
        restored = restore_backup(args.restore)
        print(f"OK  Geri yüklenen grup: {restored}")
        print(f"YEDEK: {args.restore}")
        return 0

    analysis = build_analysis()
    mode = "execute" if args.execute else "dry_run"
    analysis["mode"] = mode
    report = write_report(analysis, mode)
    summary = analysis["summary"]
    print(f"OK  Toplam grup: {summary['group_count']}")
    print(f"OK  Güvenle silinebilir: {summary['safe_to_delete_count']}")
    print(f"OK  Korunacak: {summary['protected_count']}")
    print(f"OK  Taranan referans alanı: {len(analysis['reference_columns'])}")

    if args.execute:
        deleted, backup = execute_cleanup(analysis)
        print(f"OK  Silinen sahipsiz grup: {deleted}")
        print(f"YEDEK: {backup}")
        post = build_analysis()
        post["mode"] = "post_cleanup_verification"
        post_report = write_report(post, "post_cleanup_verification")
        print(f"DOĞRULAMA RAPORU: {post_report}")
    else:
        print("BİLGİ: Dry-run tamamlandı; veritabanında değişiklik yapılmadı.")
    print(f"RAPOR: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
