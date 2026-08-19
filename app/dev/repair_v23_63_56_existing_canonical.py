
from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "products.db"

GP_ID = 142
VARIANT_ID = 174
RAW_IDS = (184, 185)
CONTROL_GP = 148

OLD_IDENTITY_KEY = "dc9ae29dec03c82af0c296c05d7a921d"
OLD_IDENTITY_SOURCE = "identity_v3:brand=samsung|family=galaxy tab a11|storage=128gb"

TARGET_IDENTITY_SOURCE = (
    "identity_v3:"
    "brand=samsung|"
    "family=galaxy tab a11+|"
    "ram=6gb|"
    "storage=128gb"
)
TARGET_IDENTITY_KEY = hashlib.sha256(
    TARGET_IDENTITY_SOURCE.encode("utf-8")
).hexdigest()[:32]

EXPECTED_TARGET_KEY = "7e647cdc7b2919f9bc6bcf7d011e4b28"

if TARGET_IDENTITY_KEY != EXPECTED_TARGET_KEY:
    raise RuntimeError(
        "Target identity hash mismatch {} != {}".format(
            TARGET_IDENTITY_KEY,
            EXPECTED_TARGET_KEY,
        )
    )

db = sqlite3.connect(str(DB))
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys=ON")

try:
    db.execute("BEGIN IMMEDIATE")

    # ------------------------------------------------------------
    # A) Exact GP142 precondition.
    # ------------------------------------------------------------
    gp = db.execute(
        """
        SELECT
            id,identity_key,identity_source,canonical_name,
            normalized_brand,family,model,variant,
            ram_gb,storage_gb,model_code,
            raw_product_count,active_offer_count,status
        FROM global_products
        WHERE id=?
        """,
        (GP_ID,),
    ).fetchone()

    if gp is None:
        raise RuntimeError("GP142 missing")

    expected_gp = (
        142,
        OLD_IDENTITY_KEY,
        OLD_IDENTITY_SOURCE,
        "Samsung Galaxy Tab A11 8GB 128GB Gümüş Tablet",
        "samsung",
        "galaxy tab a11",
        None,
        None,
        8,
        128,
        "galaxy tab a11",
        2,
        2,
        "ACTIVE",
    )

    if tuple(gp) != expected_gp:
        raise RuntimeError(
            "GP142 precondition drift: {}".format(tuple(gp))
        )

    # ------------------------------------------------------------
    # B) GP148 exact snapshot lock.
    # ------------------------------------------------------------
    gp148 = db.execute(
        """
        SELECT
            id,identity_key,identity_source,canonical_name,
            normalized_brand,family,model,variant,
            ram_gb,storage_gb,model_code,
            raw_product_count,active_offer_count,status
        FROM global_products
        WHERE id=?
        """,
        (CONTROL_GP,),
    ).fetchone()

    if gp148 is None:
        raise RuntimeError("GP148 missing")

    gp148_before = tuple(gp148)

    # ------------------------------------------------------------
    # C) No target identity collision.
    # ------------------------------------------------------------
    key_owner = db.execute(
        """
        SELECT id
        FROM global_products
        WHERE identity_key=?
          AND id<>?
        """,
        (TARGET_IDENTITY_KEY, GP_ID),
    ).fetchall()

    source_owner = db.execute(
        """
        SELECT id
        FROM global_products
        WHERE identity_source=?
          AND id<>?
        """,
        (TARGET_IDENTITY_SOURCE, GP_ID),
    ).fetchall()

    if key_owner or source_owner:
        raise RuntimeError(
            "Target identity collision key={} source={}".format(
                [r["id"] for r in key_owner],
                [r["id"] for r in source_owner],
            )
        )

    # ------------------------------------------------------------
    # D) RAW184/185 evidence and ownership.
    # ------------------------------------------------------------
    raws = db.execute(
        """
        SELECT
            id,global_product_id,global_variant_id,
            identity_key,title_raw,reconciliation_status
        FROM raw_products
        WHERE id IN (184,185)
        ORDER BY id
        """
    ).fetchall()

    if tuple(r["id"] for r in raws) != RAW_IDS:
        raise RuntimeError(
            "RAW184/185 missing: {}".format(
                [r["id"] for r in raws]
            )
        )

    expected_title_tokens = {
        184: ("galaxy tab a11+", "6gb", "128gb"),
        185: ("galaxy tab a11+", "6gb", "128gb"),
    }

    for r in raws:
        title = str(r["title_raw"] or "").casefold().replace("_", " ")

        if (
            r["global_product_id"] != GP_ID
            or r["global_variant_id"] != VARIANT_ID
            or r["identity_key"] != OLD_IDENTITY_KEY
            or r["reconciliation_status"] != "MATCHED"
        ):
            raise RuntimeError(
                "RAW{} ownership/precondition drift: {}".format(
                    r["id"],
                    tuple(r),
                )
            )

        if not all(token in title for token in expected_title_tokens[r["id"]]):
            raise RuntimeError(
                "RAW{} marketed-variant evidence missing: {}".format(
                    r["id"],
                    r["title_raw"],
                )
            )

    # ------------------------------------------------------------
    # E) Variant 174 exact precondition.
    # ------------------------------------------------------------
    variant = db.execute(
        """
        SELECT
            id,global_product_id,variant_key,color,network,model_code
        FROM global_product_variants
        WHERE id=?
        """,
        (VARIANT_ID,),
    ).fetchone()

    expected_variant = (
        174,
        142,
        "color=gumus|model_code=galaxy tab a11",
        "gumus",
        None,
        "galaxy tab a11",
    )

    if variant is None or tuple(variant) != expected_variant:
        raise RuntimeError(
            "V174 precondition drift: {}".format(
                tuple(variant) if variant else None
            )
        )

    # Collision check for the future variant key.
    collision = db.execute(
        """
        SELECT id
        FROM global_product_variants
        WHERE global_product_id=?
          AND variant_key='color=gumus'
          AND id<>?
        """,
        (GP_ID, VARIANT_ID),
    ).fetchall()

    if collision:
        raise RuntimeError(
            "V174 target variant key collision: {}".format(
                [r["id"] for r in collision]
            )
        )

    # ------------------------------------------------------------
    # F) Offer/history ownership must already be internally correct.
    # ------------------------------------------------------------
    offer_rows = db.execute(
        """
        SELECT
            id,raw_product_id,global_product_id,global_variant_id,
            lifecycle_status,is_active,is_hidden
        FROM global_offers
        WHERE id IN (184,185)
        ORDER BY id
        """
    ).fetchall()

    if tuple(r["id"] for r in offer_rows) != (184, 185):
        raise RuntimeError("Offer184/185 missing")

    for r in offer_rows:
        if not (
            r["raw_product_id"] == r["id"]
            and r["global_product_id"] == GP_ID
            and r["global_variant_id"] == VARIANT_ID
            and r["lifecycle_status"] == "ACTIVE"
            and r["is_active"] == 1
            and r["is_hidden"] == 0
        ):
            raise RuntimeError(
                "Offer{} ownership drift: {}".format(
                    r["id"], tuple(r)
                )
            )

    history_rows = db.execute(
        """
        SELECT
            id,global_offer_id,global_product_id,global_variant_id
        FROM global_offer_price_history
        WHERE id IN (210,211)
        ORDER BY id
        """
    ).fetchall()

    if tuple(r["id"] for r in history_rows) != (210, 211):
        raise RuntimeError("History210/211 missing")

    for r in history_rows:
        if not (
            r["global_product_id"] == GP_ID
            and r["global_variant_id"] == VARIANT_ID
            and r["global_offer_id"] in (184,185)
        ):
            raise RuntimeError(
                "History{} ownership drift: {}".format(
                    r["id"], tuple(r)
                )
            )

    # ------------------------------------------------------------
    # G) Rewrite GP142 canonical identity in place.
    # ------------------------------------------------------------
    changed_gp = db.execute(
        """
        UPDATE global_products
        SET
            identity_key=?,
            identity_source=?,
            canonical_name=?,
            normalized_brand='samsung',
            family='galaxy tab a11+',
            model=NULL,
            variant=NULL,
            ram_gb=6,
            storage_gb=128,
            model_code=NULL,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (
            TARGET_IDENTITY_KEY,
            TARGET_IDENTITY_SOURCE,
            "Samsung Galaxy Tab A11+ 6GB 128GB Gri Tablet",
            GP_ID,
        ),
    ).rowcount

    if changed_gp != 1:
        raise RuntimeError(
            "GP142 update count={}".format(changed_gp)
        )

    # RAW identity keys must follow canonical identity.
    changed_raw = db.execute(
        """
        UPDATE raw_products
        SET identity_key=?
        WHERE id IN (184,185)
          AND global_product_id=142
          AND global_variant_id=174
          AND identity_key=?
        """,
        (TARGET_IDENTITY_KEY, OLD_IDENTITY_KEY),
    ).rowcount

    if changed_raw != 2:
        raise RuntimeError(
            "RAW identity update count={}".format(changed_raw)
        )

    changed_variant = db.execute(
        """
        UPDATE global_product_variants
        SET
            variant_key='color=gumus',
            model_code=NULL,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=174
          AND global_product_id=142
        """
    ).rowcount

    if changed_variant != 1:
        raise RuntimeError(
            "V174 update count={}".format(changed_variant)
        )

    # ------------------------------------------------------------
    # H) Authoritative counters.
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
              AND go.is_active=1
              AND go.is_hidden=0
              AND go.lifecycle_status='ACTIVE'
              AND go.current_price>0
        )
        """
    )

    # ------------------------------------------------------------
    # I) GP148 must remain unchanged on canonical fields.
    # Counter rebuild is expected to preserve 5/5.
    # ------------------------------------------------------------
    gp148_after = db.execute(
        """
        SELECT
            id,identity_key,identity_source,canonical_name,
            normalized_brand,family,model,variant,
            ram_gb,storage_gb,model_code,
            raw_product_count,active_offer_count,status
        FROM global_products
        WHERE id=?
        """,
        (CONTROL_GP,),
    ).fetchone()

    if gp148_after is None or tuple(gp148_after) != gp148_before:
        raise RuntimeError(
            "GP148 snapshot changed before={} after={}".format(
                gp148_before,
                tuple(gp148_after) if gp148_after else None,
            )
        )

    # ------------------------------------------------------------
    # J) Final exact-state assertions.
    # ------------------------------------------------------------
    final_gp = db.execute(
        """
        SELECT
            identity_key,identity_source,canonical_name,
            normalized_brand,family,ram_gb,storage_gb,
            model_code,status,raw_product_count,active_offer_count
        FROM global_products
        WHERE id=142
        """
    ).fetchone()

    expected_final_gp = (
        TARGET_IDENTITY_KEY,
        TARGET_IDENTITY_SOURCE,
        "Samsung Galaxy Tab A11+ 6GB 128GB Gri Tablet",
        "samsung",
        "galaxy tab a11+",
        6,
        128,
        None,
        "ACTIVE",
        2,
        2,
    )

    if final_gp is None or tuple(final_gp) != expected_final_gp:
        raise RuntimeError(
            "GP142 final state mismatch: {}".format(
                tuple(final_gp) if final_gp else None
            )
        )

    final_variant = db.execute(
        """
        SELECT id,global_product_id,variant_key,color,network,model_code
        FROM global_product_variants
        WHERE id=174
        """
    ).fetchone()

    if final_variant is None or tuple(final_variant) != (
        174,142,"color=gumus","gumus",None,None
    ):
        raise RuntimeError(
            "V174 final state mismatch: {}".format(
                tuple(final_variant) if final_variant else None
            )
        )

    raw_key_bad = db.execute(
        """
        SELECT COUNT(*)
        FROM raw_products
        WHERE id IN (184,185)
          AND identity_key != ?
        """,
        (TARGET_IDENTITY_KEY,),
    ).fetchone()[0]

    # ------------------------------------------------------------
    # K) Full integrity gate.
    # ------------------------------------------------------------
    checks = {}

    checks["gp142_raw_identity_key"] = raw_key_bad

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

    checks["history_variant_wrong_gp"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history h
        JOIN global_product_variants gv ON gv.id=h.global_variant_id
        WHERE h.global_variant_id IS NOT NULL
          AND h.global_product_id != gv.global_product_id
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

    checks["target_key_duplicate"] = db.execute(
        """
        SELECT COUNT(*) - 1
        FROM global_products
        WHERE identity_key=?
        """,
        (TARGET_IDENTITY_KEY,),
    ).fetchone()[0]

    if any(checks.values()):
        raise RuntimeError(
            "Post-repair integrity failure: {}".format(checks)
        )

    db.commit()

    print(
        "V23.63.56 repair OK: "
        "GP142=A11+ 6/128 key={}; V174=color=gumus; "
        "RAW184/185 identity relinked; GP148 untouched; integrity={}".format(
            TARGET_IDENTITY_KEY,
            checks,
        )
    )

except Exception:
    db.rollback()
    raise

finally:
    db.close()
