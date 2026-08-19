
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

CAPACITY_TARGETS = {
    39: (16, 512),
    64: (12, 512),
    74: (8, 256),
    101: (12, 256),
    123: (16, 1024),
    126: (16, 480),
    169: (32, 1024),
}

FAIL_CLOSED_GPS = (18, 120, 134, 142, 162)

VARIANT_TARGETS = {
    40:  {"gp": 39,  "new_key": "default",                 "new_model": None},
    115: {"gp": 101, "new_key": "color=siyah|network=5g", "new_model": None},
    151: {"gp": 123, "new_key": "default",                 "new_model": None},
    210: {"gp": 169, "new_key": "default",                 "new_model": None},
}

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

def trusted_rows(db, gp_id):
    return db.execute(
        """
        SELECT id,title_raw,brand_raw,model_raw,description_raw,
               specifications_raw,category_raw,reconciliation_status
        FROM raw_products
        WHERE global_product_id=?
          AND reconciliation_status != 'QUARANTINED'
        ORDER BY id
        """,
        (gp_id,),
    ).fetchall()

def capacity_consensus(db, gp_id):
    rows = trusted_rows(db, gp_id)
    values = []
    for row in rows:
        parsed = S.parse(make_product(row))
        if parsed.ram_gb is None or parsed.storage_gb is None:
            continue
        values.append((row["id"], parsed.ram_gb, parsed.storage_gb))
    return values, {(r, s) for _, r, s in values}

def fk_refs_to_variant(db, variant_id):
    refs = []
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for t in tables:
        table = t["name"]
        for fk in db.execute('PRAGMA foreign_key_list("' + table + '")').fetchall():
            if fk[2] != "global_product_variants":
                continue
            source_column = fk[3]
            count = db.execute(
                'SELECT COUNT(*) FROM "' + table + '" WHERE "' + source_column + '"=?',
                (variant_id,),
            ).fetchone()[0]
            refs.append((table, source_column, count))
    return refs

def relink_variant_refs(db, source_id, target_id):
    changed = []
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for t in tables:
        table = t["name"]
        for fk in db.execute('PRAGMA foreign_key_list("' + table + '")').fetchall():
            if fk[2] != "global_product_variants":
                continue
            source_column = fk[3]
            count = db.execute(
                'UPDATE "' + table + '" SET "' + source_column + '"=? WHERE "' + source_column + '"=?',
                (target_id, source_id),
            ).rowcount
            if count:
                changed.append((table, source_column, count))
    return changed

db = sqlite3.connect(str(DB))
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys=ON")

try:
    db.execute("BEGIN IMMEDIATE")

    repaired = []

    for gp_id, expected in CAPACITY_TARGETS.items():
        gp = db.execute(
            "SELECT id,ram_gb,storage_gb,status FROM global_products WHERE id=?",
            (gp_id,),
        ).fetchone()

        if gp is None or gp["status"] != "ACTIVE":
            raise RuntimeError("GP{} missing/inactive".format(gp_id))

        parsed_values, caps = capacity_consensus(db, gp_id)

        if not parsed_values:
            raise RuntimeError("GP{} no usable parsed capacity evidence".format(gp_id))

        if caps != {expected}:
            raise RuntimeError(
                "GP{} capacity consensus mismatch expected={} got={} rows={}".format(
                    gp_id, expected, caps, parsed_values
                )
            )

        db.execute(
            """
            UPDATE global_products
            SET ram_gb=?,storage_gb=?,updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (expected[0], expected[1], gp_id),
        )
        repaired.append((gp_id, expected))

    fail_closed_snapshot = {}
    for gp_id in FAIL_CLOSED_GPS:
        row = db.execute(
            """
            SELECT id,identity_key,canonical_name,ram_gb,storage_gb,model_code,status
            FROM global_products WHERE id=?
            """,
            (gp_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Fail-closed GP{} missing".format(gp_id))
        fail_closed_snapshot[gp_id] = tuple(row)

    variant_actions = []

    for source_id, plan in VARIANT_TARGETS.items():
        source = db.execute(
            """
            SELECT id,global_product_id,variant_key,model_code
            FROM global_product_variants WHERE id=?
            """,
            (source_id,),
        ).fetchone()

        if source is None:
            raise RuntimeError("Variant {} missing".format(source_id))

        if source["global_product_id"] != plan["gp"]:
            raise RuntimeError(
                "Variant {} GP mismatch".format(source_id)
            )

        target = db.execute(
            """
            SELECT id,variant_key
            FROM global_product_variants
            WHERE global_product_id=? AND variant_key=? AND id<>?
            LIMIT 1
            """,
            (plan["gp"], plan["new_key"], source_id),
        ).fetchone()

        if target is None:
            db.execute(
                """
                UPDATE global_product_variants
                SET variant_key=?,model_code=?,updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (plan["new_key"], plan["new_model"], source_id),
            )
            variant_actions.append((source_id, "UPDATED_IN_PLACE", plan["new_key"]))
        else:
            changed = relink_variant_refs(db, source_id, target["id"])
            remaining = [x for x in fk_refs_to_variant(db, source_id) if x[2] != 0]
            if remaining:
                raise RuntimeError(
                    "Variant {} refs remain {}".format(source_id, remaining)
                )
            deleted = db.execute(
                "DELETE FROM global_product_variants WHERE id=?",
                (source_id,),
            ).rowcount
            if deleted != 1:
                raise RuntimeError(
                    "Variant {} delete count={}".format(source_id, deleted)
                )
            variant_actions.append(
                (source_id, "COLLAPSED_TO_{}".format(target["id"]), plan["new_key"], changed)
            )

    # Assert fail-closed records truly unchanged.
    for gp_id, before in fail_closed_snapshot.items():
        after = db.execute(
            """
            SELECT id,identity_key,canonical_name,ram_gb,storage_gb,model_code,status
            FROM global_products WHERE id=?
            """,
            (gp_id,),
        ).fetchone()
        if tuple(after) != before:
            raise RuntimeError("Fail-closed GP{} changed".format(gp_id))

    db.execute(
        """
        UPDATE global_products
        SET raw_product_count=(
            SELECT COUNT(*) FROM raw_products rp
            WHERE rp.global_product_id=global_products.id
        )
        """
    )

    db.execute(
        """
        UPDATE global_products
        SET active_offer_count=(
            SELECT COUNT(*) FROM global_offers go
            WHERE go.global_product_id=global_products.id
              AND go.is_active=1
              AND go.is_hidden=0
              AND go.lifecycle_status='ACTIVE'
              AND go.current_price>0
        )
        """
    )

    checks = {}

    checks["variant_drift"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offers go
        JOIN raw_products rp ON rp.id=go.raw_product_id
        WHERE go.is_active=1
          AND go.global_variant_id IS NOT NULL
          AND rp.global_variant_id IS NOT NULL
          AND go.global_variant_id != rp.global_variant_id
        """
    ).fetchone()[0]

    checks["offer_variant_wrong_gp"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offers go
        JOIN global_product_variants gv ON gv.id=go.global_variant_id
        WHERE go.global_variant_id IS NOT NULL
          AND go.global_product_id != gv.global_product_id
        """
    ).fetchone()[0]

    checks["raw_variant_wrong_gp"] = db.execute(
        """
        SELECT COUNT(*)
        FROM raw_products rp
        JOIN global_product_variants gv ON gv.id=rp.global_variant_id
        WHERE rp.global_variant_id IS NOT NULL
          AND rp.global_product_id != gv.global_product_id
        """
    ).fetchone()[0]

    checks["raw_counter"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.raw_product_count != (
            SELECT COUNT(*) FROM raw_products rp
            WHERE rp.global_product_id=gp.id
        )
        """
    ).fetchone()[0]

    checks["offer_counter"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.active_offer_count != (
            SELECT COUNT(*) FROM global_offers go
            WHERE go.global_product_id=gp.id
              AND go.is_active=1
              AND go.is_hidden=0
              AND go.lifecycle_status='ACTIVE'
              AND go.current_price>0
        )
        """
    ).fetchone()[0]

    checks["quarantine"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offers
        WHERE lifecycle_status='QUARANTINED'
          AND (is_active=1 OR is_hidden=0)
        """
    ).fetchone()[0]

    checks["duplicate_variant_keys"] = db.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT global_product_id,variant_key,COUNT(*) c
            FROM global_product_variants
            GROUP BY global_product_id,variant_key
            HAVING COUNT(*)>1
        )
        """
    ).fetchone()[0]

    if any(checks.values()):
        raise RuntimeError("Post-repair integrity failure: {}".format(checks))

    for gp_id, expected in CAPACITY_TARGETS.items():
        row = db.execute(
            "SELECT ram_gb,storage_gb FROM global_products WHERE id=?",
            (gp_id,),
        ).fetchone()
        if (row["ram_gb"], row["storage_gb"]) != expected:
            raise RuntimeError("GP{} post-repair mismatch".format(gp_id))

    db.commit()

    print(
        "V23.63.53 repair OK: capacity={}; variants={}; "
        "fail_closed={}; integrity={}".format(
            repaired, variant_actions, list(FAIL_CLOSED_GPS), checks
        )
    )

except Exception:
    db.rollback()
    raise
finally:
    db.close()
