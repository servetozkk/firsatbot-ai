from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, delete, insert, select, update

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine


def latest_backup() -> Path:
    folder = ROOT / "data" / "backups" / "group_merge"
    files = sorted(folder.glob("v11_2_4_before_merge_*.json"), reverse=True)
    if not files:
        raise RuntimeError("v11.2.4 yedeği bulunamadı.")
    return files[0]


def clean_row(row: dict[str, Any], table: Table) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k in table.c}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup", type=Path, default=None)
    args = parser.parse_args()
    path = args.backup or latest_backup()
    data = json.loads(path.read_text(encoding="utf-8"))

    metadata = MetaData()
    groups = Table("product_groups", metadata, autoload_with=engine)
    specs = Table("product_feature_values", metadata, autoload_with=engine)
    source_id = int(data["source_group_id"])
    target_id = int(data["target_group_id"])
    source_group = clean_row(data["source_group"], groups)
    source_specs = [clean_row(r, specs) for r in data["source_specifications"]]

    with engine.begin() as conn:
        exists = conn.execute(select(groups.c.id).where(groups.c.id == source_id)).first()
        if not exists:
            conn.execute(insert(groups).values(**source_group))

        source_spec_ids = {int(r["id"]) for r in source_specs}
        for row in source_specs:
            row_id = int(row["id"])
            existing = conn.execute(select(specs).where(specs.c.id == row_id)).mappings().first()
            if existing:
                conn.execute(update(specs).where(specs.c.id == row_id).values(**row))
            else:
                # Aynı hedef feature kaydı özgün kaynak kaydının geri eklenmesini engelleyebilir.
                feature_id = int(row["feature_id"])
                target_same = conn.execute(select(specs).where(
                    specs.c.product_group_id == target_id,
                    specs.c.feature_id == feature_id,
                )).mappings().first()
                if target_same and int(target_same["id"]) not in source_spec_ids:
                    # Bu kayıt birleştirme öncesinde hedefte zaten vardı; kaynak kopyası güvenle geri eklenebilir
                    # çünkü farklı product_group_id benzersizlik koşulunu bozmaz.
                    pass
                conn.execute(insert(specs).values(**row))

    print(f"OK  Kaynak grup geri yüklendi: {source_id}")
    print(f"OK  Specification geri yüklendi: {len(source_specs)}")
    print(f"YEDEK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
