
from __future__ import annotations
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

DB = ROOT / "data" / "products.db"

def parse_specs(value):
    if not value:
        return None
    try:
        obj = json.loads(value)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return value

def make_product(row):
    return SimpleNamespace(
        name=row["title_raw"] or "",
        brand=row["brand_raw"] or "",
        model=row["model_raw"] or "",
        description=row["description_raw"] or "",
        specifications=parse_specs(row["specifications_raw"]),
        category=row["category_raw"] or "",
        product_code="",
    )

db = sqlite3.connect(str(DB))
db.row_factory = sqlite3.Row

try:
    db.execute("BEGIN IMMEDIATE")

    # GP174: capacity-only repair. Do NOT rewrite identity_key/source in this release.
    rows = db.execute(
        """
        SELECT id,title_raw,brand_raw,model_raw,description_raw,
               specifications_raw,category_raw,reconciliation_status
        FROM raw_products
        WHERE global_product_id=174
        ORDER BY id
        """
    ).fetchall()

    trusted = [r for r in rows if r["reconciliation_status"] != "QUARANTINED"]
    if not trusted:
        raise RuntimeError("GP174 trusted raw missing")

    for row in trusted:
        parsed = S.parse(make_product(row))
        if (
            parsed.brand != "casper"
            or parsed.ram_gb != 16
            or parsed.storage_gb != 1024
            or parsed.model_code != "x650.1342-bf00x-g-f"
        ):
            raise RuntimeError(
                f"GP174 evidence conflict raw={row['id']} "
                f"brand={parsed.brand} ram={parsed.ram_gb} "
                f"storage={parsed.storage_gb} model={parsed.model_code}"
            )

    db.execute(
        """
        UPDATE global_products
        SET ram_gb=16,
            storage_gb=1024,
            model_code='x650.1342-bf00x-g-f',
            updated_at=CURRENT_TIMESTAMP
        WHERE id=174
        """
    )

    # GP170: status-retire only when absolutely childless. No delete.
    gp170 = db.execute(
        """
        SELECT raw_product_count,active_offer_count
        FROM global_products
        WHERE id=170
        """
    ).fetchone()

    retired = 0
    if gp170 is not None:
        actual_raw = db.execute(
            "SELECT COUNT(*) FROM raw_products WHERE global_product_id=170"
        ).fetchone()[0]
        actual_offer = db.execute(
            "SELECT COUNT(*) FROM global_offers WHERE global_product_id=170"
        ).fetchone()[0]
        variant_count = db.execute(
            "SELECT COUNT(*) FROM global_product_variants WHERE global_product_id=170"
        ).fetchone()[0]

        if (
            gp170["raw_product_count"] == 0
            and gp170["active_offer_count"] == 0
            and actual_raw == 0
            and actual_offer == 0
            and variant_count == 0
        ):
            db.execute(
                """
                UPDATE global_products
                SET status='RETIRED',
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=170
                """
            )
            retired = 1

    # Explicitly assert Xaser rows are untouched by this repair.
    xaser_before = db.execute(
        """
        SELECT id,ram_gb,storage_gb,identity_key
        FROM global_products
        WHERE id IN (28,173)
        ORDER BY id
        """
    ).fetchall()
    if len(xaser_before) != 2:
        raise RuntimeError("GP28/GP173 fail-closed rows missing")

    db.commit()
    print(
        f"V23.63.51 repair OK: GP174=16/1024; "
        f"GP170 retired={retired}; GP28/GP173 untouched"
    )
except Exception:
    db.rollback()
    raise
finally:
    db.close()
