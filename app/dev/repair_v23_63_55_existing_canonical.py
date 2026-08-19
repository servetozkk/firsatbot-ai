
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "products.db"

TARGET_HISTORY_IDS = (208, 209, 212)
SOURCE_GP = 142
TARGET_GP = 148
TARGET_VARIANT = 183
PRESERVE_VARIANTS = (18, 27, 154, 155, 170, 188)

db = sqlite3.connect(str(DB))
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys=ON")

try:
    db.execute("BEGIN IMMEDIATE")

    # ------------------------------------------------------------
    # A) The only pre-existing history wrong-GP rows must be the
    # three audited residues. Any extra anomaly => fail closed.
    # ------------------------------------------------------------
    wrong_before = db.execute(
        """
        SELECT
            h.id,
            h.global_offer_id,
            h.global_product_id AS history_gp,
            h.global_variant_id AS history_variant,
            gv.global_product_id AS variant_gp,
            go.global_product_id AS offer_gp,
            go.global_variant_id AS offer_variant,
            go.raw_product_id,
            rp.global_product_id AS raw_gp,
            rp.global_variant_id AS raw_variant
        FROM global_offer_price_history h
        JOIN global_product_variants gv
          ON gv.id=h.global_variant_id
        JOIN global_offers go
          ON go.id=h.global_offer_id
        JOIN raw_products rp
          ON rp.id=go.raw_product_id
        WHERE h.global_variant_id IS NOT NULL
          AND h.global_product_id != gv.global_product_id
        ORDER BY h.id
        """
    ).fetchall()

    wrong_ids = tuple(row["id"] for row in wrong_before)

    if wrong_ids != TARGET_HISTORY_IDS:
        raise RuntimeError(
            "Unexpected history wrong-GP baseline: {}".format(wrong_ids)
        )

    # ------------------------------------------------------------
    # B) Snapshot no-write scopes.
    # ------------------------------------------------------------
    preserve_snapshot = {}

    for vid in PRESERVE_VARIANTS:
        row = db.execute(
            """
            SELECT id,global_product_id,variant_key,color,network,model_code
            FROM global_product_variants
            WHERE id=?
            """,
            (vid,),
        ).fetchone()

        if row is None:
            raise RuntimeError("PRESERVE V{} missing".format(vid))

        preserve_snapshot[vid] = tuple(row)

    gp_snapshot = {}

    for gp_id in (142, 148):
        row = db.execute(
            """
            SELECT
                id,identity_key,identity_source,canonical_name,
                normalized_brand,family,model,variant,
                ram_gb,storage_gb,model_code,status
            FROM global_products
            WHERE id=?
            """,
            (gp_id,),
        ).fetchone()

        if row is None:
            raise RuntimeError("GP{} missing".format(gp_id))

        gp_snapshot[gp_id] = tuple(row)

    # ------------------------------------------------------------
    # C) Revalidate each audited history row.
    # Variant is already V183; only canonical history owner GP is stale.
    # ------------------------------------------------------------
    repaired = []

    for row in wrong_before:
        hid = row["id"]

        if not (
            row["history_gp"] == SOURCE_GP
            and row["history_variant"] == TARGET_VARIANT
            and row["variant_gp"] == TARGET_GP
            and row["offer_gp"] == TARGET_GP
            and row["offer_variant"] == TARGET_VARIANT
            and row["raw_gp"] == TARGET_GP
            and row["raw_variant"] == TARGET_VARIANT
        ):
            raise RuntimeError(
                "H{} ownership evidence changed: "
                "hist=GP{}/V{} variantGP={} offer=GP{}/V{} raw=GP{}/V{}".format(
                    hid,
                    row["history_gp"],
                    row["history_variant"],
                    row["variant_gp"],
                    row["offer_gp"],
                    row["offer_variant"],
                    row["raw_gp"],
                    row["raw_variant"],
                )
            )

        changed = db.execute(
            """
            UPDATE global_offer_price_history
            SET global_product_id=?
            WHERE id=?
              AND global_product_id=?
              AND global_variant_id=?
            """,
            (TARGET_GP, hid, SOURCE_GP, TARGET_VARIANT),
        ).rowcount

        if changed != 1:
            raise RuntimeError(
                "H{} update count={}".format(hid, changed)
            )

        repaired.append(hid)

    # ------------------------------------------------------------
    # D) Preserve scopes must remain byte-equivalent on selected fields.
    # ------------------------------------------------------------
    for vid, before in preserve_snapshot.items():
        after = db.execute(
            """
            SELECT id,global_product_id,variant_key,color,network,model_code
            FROM global_product_variants
            WHERE id=?
            """,
            (vid,),
        ).fetchone()

        if after is None or tuple(after) != before:
            raise RuntimeError("PRESERVE V{} changed".format(vid))

    for gp_id, before in gp_snapshot.items():
        after = db.execute(
            """
            SELECT
                id,identity_key,identity_source,canonical_name,
                normalized_brand,family,model,variant,
                ram_gb,storage_gb,model_code,status
            FROM global_products
            WHERE id=?
            """,
            (gp_id,),
        ).fetchone()

        if after is None or tuple(after) != before:
            raise RuntimeError("GP{} canonical changed".format(gp_id))

    # ------------------------------------------------------------
    # E) Authoritative counter rebuild.
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

    checks["history_wrong_gp"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history h
        JOIN global_product_variants gv
          ON gv.id=h.global_variant_id
        WHERE h.global_variant_id IS NOT NULL
          AND h.global_product_id != gv.global_product_id
        """
    ).fetchone()[0]

    checks["target_history_not_gp148_v183"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history
        WHERE id IN (208,209,212)
          AND (
              global_product_id != 148
              OR global_variant_id != 183
          )
        """
    ).fetchone()[0]

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
        raise RuntimeError(
            "Post-repair integrity failure: {}".format(checks)
        )

    db.commit()

    print(
        "V23.63.55 repair OK: history_ids={}; "
        "GP142/GP148 canonical untouched; preserve={}; integrity={}".format(
            repaired,
            list(PRESERVE_VARIANTS),
            checks,
        )
    )

except Exception:
    db.rollback()
    raise

finally:
    db.close()
