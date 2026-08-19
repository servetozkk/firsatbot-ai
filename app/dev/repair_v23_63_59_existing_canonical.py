
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "products.db"

ALLOWLIST = (
    15, 17, 26, 46, 77,
    126, 129, 130, 131, 133,
    135, 136, 138, 139, 150,
    152, 153, 156, 163, 170,
)

EXPECTED_STATUS = {
    15: "MERGED",
    17: "MERGED",
    26: "MERGED",
    46: "MERGED",
    77: "RETIRED",
    126: "MERGED",
    129: "RETIRED",
    130: "RETIRED",
    131: "RETIRED",
    133: "MERGED",
    135: "MERGED",
    136: "MERGED",
    138: "MERGED",
    139: "MERGED",
    150: "MERGED",
    152: "MERGED",
    153: "MERGED",
    156: "MERGED",
    163: "MERGED",
    170: "RETIRED",
}

db = sqlite3.connect(str(DB))
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys=ON")

try:
    db.execute("BEGIN IMMEDIATE")

    # ------------------------------------------------------------
    # A) Baseline integrity must already be clean.
    # ------------------------------------------------------------
    baseline = {}

    baseline["history_wrong_gp"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history h
        JOIN global_product_variants gv
          ON gv.id=h.global_variant_id
        WHERE h.global_variant_id IS NOT NULL
          AND h.global_product_id != gv.global_product_id
        """
    ).fetchone()[0]

    baseline["variant_drift"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offers go
        JOIN raw_products rp
          ON rp.id=go.raw_product_id
        WHERE go.is_active=1
          AND go.global_variant_id IS NOT NULL
          AND rp.global_variant_id IS NOT NULL
          AND go.global_variant_id != rp.global_variant_id
        """
    ).fetchone()[0]

    baseline["offer_variant_wrong_gp"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offers go
        JOIN global_product_variants gv
          ON gv.id=go.global_variant_id
        WHERE go.global_variant_id IS NOT NULL
          AND go.global_product_id != gv.global_product_id
        """
    ).fetchone()[0]

    baseline["raw_variant_wrong_gp"] = db.execute(
        """
        SELECT COUNT(*)
        FROM raw_products rp
        JOIN global_product_variants gv
          ON gv.id=rp.global_variant_id
        WHERE rp.global_variant_id IS NOT NULL
          AND rp.global_product_id != gv.global_product_id
        """
    ).fetchone()[0]

    baseline["raw_counter"] = db.execute(
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

    baseline["offer_counter"] = db.execute(
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

    baseline["quarantine"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offers
        WHERE lifecycle_status='QUARANTINED'
          AND (is_active=1 OR is_hidden=0)
        """
    ).fetchone()[0]

    baseline["duplicate_variant_keys"] = db.execute(
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

    if any(baseline.values()):
        raise RuntimeError(
            "Pre-repair baseline not clean: {}".format(baseline)
        )

    # ------------------------------------------------------------
    # B) Exact allowlist preconditions.
    # ------------------------------------------------------------
    snapshot = {}

    for gp_id in ALLOWLIST:
        gp = db.execute(
            """
            SELECT
                id,
                status,
                identity_key,
                identity_source,
                canonical_name,
                raw_product_count,
                active_offer_count
            FROM global_products
            WHERE id=?
            """,
            (gp_id,),
        ).fetchone()

        if gp is None:
            raise RuntimeError(
                "Allowlist GP{} missing".format(gp_id)
            )

        if gp["status"] != EXPECTED_STATUS[gp_id]:
            raise RuntimeError(
                "GP{} status drift {} != {}".format(
                    gp_id,
                    gp["status"],
                    EXPECTED_STATUS[gp_id],
                )
            )

        refs = {
            "raw": db.execute(
                "SELECT COUNT(*) FROM raw_products WHERE global_product_id=?",
                (gp_id,),
            ).fetchone()[0],
            "offer": db.execute(
                "SELECT COUNT(*) FROM global_offers WHERE global_product_id=?",
                (gp_id,),
            ).fetchone()[0],
            "variant": db.execute(
                "SELECT COUNT(*) FROM global_product_variants WHERE global_product_id=?",
                (gp_id,),
            ).fetchone()[0],
            "history": db.execute(
                "SELECT COUNT(*) FROM global_offer_price_history WHERE global_product_id=?",
                (gp_id,),
            ).fetchone()[0],
        }

        if any(refs.values()):
            raise RuntimeError(
                "GP{} is not zero-reference: {}".format(
                    gp_id,
                    refs,
                )
            )

        if gp["raw_product_count"] != 0 or gp["active_offer_count"] != 0:
            raise RuntimeError(
                "GP{} counters are not zero raw={} offer={}".format(
                    gp_id,
                    gp["raw_product_count"],
                    gp["active_offer_count"],
                )
            )

        snapshot[gp_id] = tuple(gp)

    # ------------------------------------------------------------
    # C) Delete only explicit audited rows.
    # ------------------------------------------------------------
    deleted = []

    for gp_id in ALLOWLIST:
        count = db.execute(
            """
            DELETE FROM global_products
            WHERE id=?
              AND status IN ('MERGED','RETIRED')
              AND raw_product_count=0
              AND active_offer_count=0
            """,
            (gp_id,),
        ).rowcount

        if count != 1:
            raise RuntimeError(
                "GP{} delete count={}".format(
                    gp_id,
                    count,
                )
            )

        deleted.append(gp_id)

    # ------------------------------------------------------------
    # D) Exact postconditions.
    # ------------------------------------------------------------
    checks = {}

    checks["allowlist_remaining"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_products
        WHERE id IN (
            15,17,26,46,77,
            126,129,130,131,133,
            135,136,138,139,150,
            152,153,156,163,170
        )
        """
    ).fetchone()[0]

    checks["empty_nonactive_remaining"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.status IN ('MERGED','RETIRED')
          AND gp.raw_product_count=0
          AND gp.active_offer_count=0
          AND NOT EXISTS (
              SELECT 1 FROM raw_products rp
              WHERE rp.global_product_id=gp.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM global_offers go
              WHERE go.global_product_id=gp.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM global_product_variants gv
              WHERE gv.global_product_id=gp.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM global_offer_price_history h
              WHERE h.global_product_id=gp.id
          )
        """
    ).fetchone()[0]

    checks["history_under_nonactive"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history h
        JOIN global_products gp
          ON gp.id=h.global_product_id
        WHERE gp.status IN ('MERGED','RETIRED')
        """
    ).fetchone()[0]

    checks["variants_under_nonactive"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_product_variants gv
        JOIN global_products gp
          ON gp.id=gv.global_product_id
        WHERE gp.status IN ('MERGED','RETIRED')
        """
    ).fetchone()[0]

    checks["raw_identity_drift"] = db.execute(
        """
        SELECT COUNT(*)
        FROM raw_products rp
        JOIN global_products gp
          ON gp.id=rp.global_product_id
        WHERE rp.identity_key IS NOT NULL
          AND gp.identity_key IS NOT NULL
          AND rp.identity_key != gp.identity_key
        """
    ).fetchone()[0]

    checks["duplicate_identity_keys"] = db.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT identity_key,COUNT(*) c
            FROM global_products
            WHERE identity_key IS NOT NULL
            GROUP BY identity_key
            HAVING COUNT(*)>1
        )
        """
    ).fetchone()[0]

    checks["duplicate_identity_sources"] = db.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT identity_source,COUNT(*) c
            FROM global_products
            WHERE identity_source IS NOT NULL
            GROUP BY identity_source
            HAVING COUNT(*)>1
        )
        """
    ).fetchone()[0]

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

    checks["variant_drift"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offers go
        JOIN raw_products rp
          ON rp.id=go.raw_product_id
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
        JOIN global_product_variants gv
          ON gv.id=go.global_variant_id
        WHERE go.global_variant_id IS NOT NULL
          AND go.global_product_id != gv.global_product_id
        """
    ).fetchone()[0]

    checks["raw_variant_wrong_gp"] = db.execute(
        """
        SELECT COUNT(*)
        FROM raw_products rp
        JOIN global_product_variants gv
          ON gv.id=rp.global_variant_id
        WHERE rp.global_variant_id IS NOT NULL
          AND rp.global_product_id != gv.global_product_id
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

    if any(checks.values()):
        raise RuntimeError(
            "Post-repair integrity failure: {}".format(
                checks
            )
        )

    db.commit()

    print(
        "V23.63.59 repair OK: deleted={}; integrity={}".format(
            deleted,
            checks,
        )
    )

except Exception:
    db.rollback()
    raise

finally:
    db.close()
