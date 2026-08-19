
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
SOURCE_VARIANT_ID = 211
TARGET_GP_ID = 173
TARGET_VARIANT_ID = 214

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
db.execute("PRAGMA foreign_keys=ON")

try:
    db.execute("BEGIN IMMEDIATE")

    # ------------------------------------------------------------
    # A) GP173 capacity-only repair.
    # Exclude SOURCE_IDENTITY quarantine; PRICE_QUARANTINED remains
    # valid identity/capacity evidence.
    # ------------------------------------------------------------
    gp173 = db.execute(
        """
        SELECT id,ram_gb,storage_gb,identity_key,canonical_name
        FROM global_products
        WHERE id=173
        """
    ).fetchone()

    if gp173 is None:
        raise RuntimeError("GP173 missing")

    raws173 = db.execute(
        """
        SELECT id,title_raw,brand_raw,model_raw,description_raw,
               specifications_raw,category_raw,reconciliation_status
        FROM raw_products
        WHERE global_product_id=173
        ORDER BY id
        """
    ).fetchall()

    trusted173 = [
        row for row in raws173
        if row["reconciliation_status"] != "QUARANTINED"
    ]

    if len(trusted173) < 2:
        raise RuntimeError("GP173 insufficient trusted raw evidence")

    parsed_caps = []
    for row in trusted173:
        parsed = S.parse(make_product(row))
        parsed_caps.append(
            (row["id"], parsed.brand, parsed.ram_gb, parsed.storage_gb)
        )

    bad = [
        item for item in parsed_caps
        if item[1] != "xaser" or item[2] != 32 or item[3] != 1024
    ]
    if bad:
        raise RuntimeError(f"GP173 capacity consensus conflict: {bad}")

    # Capacity-only: do not rewrite identity_key/source/family/model/name.
    db.execute(
        """
        UPDATE global_products
        SET ram_gb=32,
            storage_gb=1024,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=173
        """
    )

    # ------------------------------------------------------------
    # B) Variant211 price-history relink.
    # Every history row must still point through its global_offer_id
    # to current offer GP173/Variant214 AND raw GP173/Variant214.
    # This includes quarantined offer 333: quarantine affects serving,
    # not the offer-linked ownership provenance.
    # ------------------------------------------------------------
    history_rows = db.execute(
        """
        SELECT
            h.id,
            h.global_offer_id,
            h.global_product_id AS hist_gp,
            h.global_variant_id AS hist_variant,
            go.global_product_id AS offer_gp,
            go.global_variant_id AS offer_variant,
            go.raw_product_id,
            rp.global_product_id AS raw_gp,
            rp.global_variant_id AS raw_variant
        FROM global_offer_price_history h
        JOIN global_offers go
          ON go.id=h.global_offer_id
        JOIN raw_products rp
          ON rp.id=go.raw_product_id
        WHERE h.global_variant_id=?
        ORDER BY h.id
        """,
        (SOURCE_VARIANT_ID,),
    ).fetchall()

    if len(history_rows) != 3:
        raise RuntimeError(
            f"Variant211 expected 3 history rows, got {len(history_rows)}"
        )

    for row in history_rows:
        if not (
            row["offer_gp"] == TARGET_GP_ID
            and row["offer_variant"] == TARGET_VARIANT_ID
            and row["raw_gp"] == TARGET_GP_ID
            and row["raw_variant"] == TARGET_VARIANT_ID
        ):
            raise RuntimeError(
                "Unsafe history relink row={} offer_gp={} offer_var={} "
                "raw_gp={} raw_var={}".format(
                    row["id"],
                    row["offer_gp"],
                    row["offer_variant"],
                    row["raw_gp"],
                    row["raw_variant"],
                )
            )

    db.execute(
        """
        UPDATE global_offer_price_history
        SET global_product_id=?,
            global_variant_id=?
        WHERE global_variant_id=?
          AND global_offer_id IN (29,332,333)
        """,
        (TARGET_GP_ID, TARGET_VARIANT_ID, SOURCE_VARIANT_ID),
    )

    remaining_history = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history
        WHERE global_variant_id=?
        """,
        (SOURCE_VARIANT_ID,),
    ).fetchone()[0]

    if remaining_history != 0:
        raise RuntimeError(
            f"Variant211 history refs remain: {remaining_history}"
        )

    # ------------------------------------------------------------
    # C) Delete Variant211 only if every FK reference is zero.
    # ------------------------------------------------------------
    ref_tables = []

    tables = db.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    for table_row in tables:
        table = table_row["name"]
        fks = db.execute(
            f'PRAGMA foreign_key_list("{table}")'
        ).fetchall()

        for fk in fks:
            target_table = fk[2]
            source_column = fk[3]

            if target_table != "global_product_variants":
                continue

            count = db.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{source_column}"=?',
                (SOURCE_VARIANT_ID,),
            ).fetchone()[0]

            ref_tables.append((table, source_column, count))

    nonzero = [
        item for item in ref_tables
        if item[2] != 0
    ]

    if nonzero:
        raise RuntimeError(
            f"Variant211 FK refs remain: {nonzero}"
        )

    deleted_variant = db.execute(
        """
        DELETE FROM global_product_variants
        WHERE id=?
          AND global_product_id=170
          AND variant_key='model_code=cozunurluk1920'
        """,
        (SOURCE_VARIANT_ID,),
    ).rowcount

    if deleted_variant != 1:
        raise RuntimeError(
            f"Variant211 delete count={deleted_variant}"
        )

    # ------------------------------------------------------------
    # D) GP170 RETIRED only after it is completely childless.
    # No delete.
    # ------------------------------------------------------------
    raw170 = db.execute(
        "SELECT COUNT(*) FROM raw_products WHERE global_product_id=170"
    ).fetchone()[0]
    offer170 = db.execute(
        "SELECT COUNT(*) FROM global_offers WHERE global_product_id=170"
    ).fetchone()[0]
    variant170 = db.execute(
        "SELECT COUNT(*) FROM global_product_variants WHERE global_product_id=170"
    ).fetchone()[0]

    if (raw170, offer170, variant170) != (0, 0, 0):
        raise RuntimeError(
            f"GP170 not childless: raw={raw170} offer={offer170} variant={variant170}"
        )

    db.execute(
        """
        UPDATE global_products
        SET status='RETIRED',
            raw_product_count=0,
            active_offer_count=0,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=170
        """
    )

    # ------------------------------------------------------------
    # E) Authoritative counter rebuild.
    # Startup continuity may restore an older richer snapshot
    # before this repair hook. Rebuild counters here atomically.
    # ------------------------------------------------------------
    db.execute(
        """
        UPDATE global_products
        SET raw_product_count = (
            SELECT COUNT(*)
            FROM raw_products rp
            WHERE rp.global_product_id = global_products.id
        )
        """
    )

    db.execute(
        """
        UPDATE global_products
        SET active_offer_count = (
            SELECT COUNT(*)
            FROM global_offers go
            WHERE go.global_product_id = global_products.id
              AND go.is_active = 1
              AND go.is_hidden = 0
              AND go.lifecycle_status = 'ACTIVE'
              AND go.current_price > 0
        )
        """
    )

    # ------------------------------------------------------------
    # F) Integrity gate.
    # ------------------------------------------------------------
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

    checks["raw_counter"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.raw_product_count != (
            SELECT COUNT(*)
            FROM raw_products rp
            WHERE rp.global_product_id=gp.id
        )
        """
    ).fetchone()[0]

    checks["offer_counter"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.active_offer_count != (
            SELECT COUNT(*)
            FROM global_offers go
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

    checks["history_variant211"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history
        WHERE global_variant_id=211
        """
    ).fetchone()[0]

    if any(checks.values()):
        raise RuntimeError(
            f"Post-repair integrity failure: {checks}"
        )

    db.commit()

    print(
        "V23.63.52 repair OK: "
        "GP173=32/1024; history211->GP173/V214 relinked=3; "
        "Variant211 deleted; GP170 RETIRED; GP28 untouched; "
        f"integrity={checks}"
    )

except Exception:
    db.rollback()
    raise

finally:
    db.close()
