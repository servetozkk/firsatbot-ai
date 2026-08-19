
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "products.db"

TARGET_VARIANTS = (18, 170)
PRESERVE_VARIANTS = (27, 154, 155, 188)

EXPECTED_HISTORY_COUNTS = {
    18: 2,
    170: 8,
}

EXPECTED_SOURCE_GPS = {
    18: 17,
    170: 139,
}

def all_variant_fk_refs(db, variant_id):
    refs = []

    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    for row in tables:
        table = row["name"]

        for fk in db.execute(
            'PRAGMA foreign_key_list("' + table + '")'
        ).fetchall():

            if fk[2] != "global_product_variants":
                continue

            column = fk[3]

            count = db.execute(
                'SELECT COUNT(*) FROM "' + table + '" WHERE "' + column + '"=?',
                (variant_id,),
            ).fetchone()[0]

            refs.append(
                (table, column, count)
            )

    return refs


db = sqlite3.connect(str(DB))
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys=ON")

try:
    db.execute("BEGIN IMMEDIATE")

    # ------------------------------------------------------------
    # A) Baseline must be clean before this repair.
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
        JOIN raw_products rp ON rp.id=go.raw_product_id
        WHERE go.is_active=1
          AND go.global_variant_id IS NOT NULL
          AND rp.global_variant_id IS NOT NULL
          AND go.global_variant_id != rp.global_variant_id
        """
    ).fetchone()[0]

    baseline["raw_counter"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.raw_product_count != (
            SELECT COUNT(*) FROM raw_products rp
            WHERE rp.global_product_id=gp.id
        )
        """
    ).fetchone()[0]

    baseline["offer_counter"] = db.execute(
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
    # B) Preserve snapshot.
    # ------------------------------------------------------------
    preserve_snapshot = {}

    for vid in PRESERVE_VARIANTS:
        row = db.execute(
            """
            SELECT
                id,global_product_id,variant_key,
                color,network,model_code
            FROM global_product_variants
            WHERE id=?
            """,
            (vid,),
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "PRESERVE V{} missing".format(vid)
            )

        preserve_snapshot[vid] = tuple(row)

    # ------------------------------------------------------------
    # C) Relink each history row using its own current offer/raw target.
    # Multi-target is allowed only because each row is independently
    # proven by matching current offer and raw ownership.
    # ------------------------------------------------------------
    relinked = []

    for source_vid in TARGET_VARIANTS:

        variant = db.execute(
            """
            SELECT
                id,global_product_id,variant_key,
                color,network,model_code
            FROM global_product_variants
            WHERE id=?
            """,
            (source_vid,),
        ).fetchone()

        if variant is None:
            raise RuntimeError(
                "Target V{} missing".format(source_vid)
            )

        if variant["global_product_id"] != EXPECTED_SOURCE_GPS[source_vid]:
            raise RuntimeError(
                "V{} source GP drift {} != {}".format(
                    source_vid,
                    variant["global_product_id"],
                    EXPECTED_SOURCE_GPS[source_vid],
                )
            )

        raw_refs = db.execute(
            "SELECT COUNT(*) FROM raw_products WHERE global_variant_id=?",
            (source_vid,),
        ).fetchone()[0]

        offer_refs = db.execute(
            "SELECT COUNT(*) FROM global_offers WHERE global_variant_id=?",
            (source_vid,),
        ).fetchone()[0]

        if raw_refs != 0 or offer_refs != 0:
            raise RuntimeError(
                "V{} became live raw={} offer={}".format(
                    source_vid,
                    raw_refs,
                    offer_refs,
                )
            )

        histories = db.execute(
            """
            SELECT
                h.id,
                h.global_offer_id,
                h.global_product_id AS history_gp,
                h.global_variant_id AS history_variant,

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
            (source_vid,),
        ).fetchall()

        expected_count = EXPECTED_HISTORY_COUNTS[source_vid]

        if len(histories) != expected_count:
            raise RuntimeError(
                "V{} history count {} != {}".format(
                    source_vid,
                    len(histories),
                    expected_count,
                )
            )

        for h in histories:

            if (
                h["offer_gp"] is None
                or h["offer_variant"] is None
                or h["raw_gp"] is None
                or h["raw_variant"] is None
            ):
                raise RuntimeError(
                    "H{} target contains NULL ownership".format(
                        h["id"]
                    )
                )

            if not (
                h["offer_gp"] == h["raw_gp"]
                and h["offer_variant"] == h["raw_variant"]
            ):
                raise RuntimeError(
                    "H{} offer/raw target disagreement "
                    "offer=GP{}/V{} raw=GP{}/V{}".format(
                        h["id"],
                        h["offer_gp"],
                        h["offer_variant"],
                        h["raw_gp"],
                        h["raw_variant"],
                    )
                )

            target_variant = db.execute(
                """
                SELECT id,global_product_id
                FROM global_product_variants
                WHERE id=?
                """,
                (h["offer_variant"],),
            ).fetchone()

            if (
                target_variant is None
                or target_variant["global_product_id"] != h["offer_gp"]
            ):
                raise RuntimeError(
                    "H{} target variant invalid GP{}/V{}".format(
                        h["id"],
                        h["offer_gp"],
                        h["offer_variant"],
                    )
                )

            changed = db.execute(
                """
                UPDATE global_offer_price_history
                SET
                    global_product_id=?,
                    global_variant_id=?
                WHERE id=?
                  AND global_variant_id=?
                """,
                (
                    h["offer_gp"],
                    h["offer_variant"],
                    h["id"],
                    source_vid,
                ),
            ).rowcount

            if changed != 1:
                raise RuntimeError(
                    "H{} update count={}".format(
                        h["id"],
                        changed,
                    )
                )

            relinked.append(
                (
                    h["id"],
                    source_vid,
                    h["history_gp"],
                    h["offer_gp"],
                    h["offer_variant"],
                )
            )

        remaining_refs = [
            ref
            for ref in all_variant_fk_refs(db, source_vid)
            if ref[2] != 0
        ]

        if remaining_refs:
            raise RuntimeError(
                "V{} FK refs remain {}".format(
                    source_vid,
                    remaining_refs,
                )
            )

        deleted = db.execute(
            "DELETE FROM global_product_variants WHERE id=?",
            (source_vid,),
        ).rowcount

        if deleted != 1:
            raise RuntimeError(
                "V{} delete count={}".format(
                    source_vid,
                    deleted,
                )
            )

    # ------------------------------------------------------------
    # D) Preserve variants must remain unchanged.
    # ------------------------------------------------------------
    for vid, before in preserve_snapshot.items():

        after = db.execute(
            """
            SELECT
                id,global_product_id,variant_key,
                color,network,model_code
            FROM global_product_variants
            WHERE id=?
            """,
            (vid,),
        ).fetchone()

        if after is None or tuple(after) != before:
            raise RuntimeError(
                "PRESERVE V{} changed".format(vid)
            )

    # ------------------------------------------------------------
    # E) Authoritative counters.
    # ------------------------------------------------------------
    db.execute(
        """
        UPDATE global_products
        SET raw_product_count=(
            SELECT COUNT(*)
            FROM raw_products rp
            WHERE rp.global_product_id=global_products.id
        )
        """
    )

    db.execute(
        """
        UPDATE global_products
        SET active_offer_count=(
            SELECT COUNT(*)
            FROM global_offers go
            WHERE go.global_product_id=global_products.id
              AND go.is_active=1
              AND go.is_hidden=0
              AND go.lifecycle_status='ACTIVE'
              AND go.current_price>0
        )
        """
    )

    # ------------------------------------------------------------
    # F) Final integrity gate.
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

    checks["target_variants_remaining"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_product_variants
        WHERE id IN (18,170)
        """
    ).fetchone()[0]

    checks["target_history_remaining"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history
        WHERE global_variant_id IN (18,170)
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
        "V23.63.57 repair OK: "
        "relinked={}; deleted=[18,170]; "
        "preserved=[27,154,155,188]; integrity={}".format(
            relinked,
            checks,
        )
    )

except Exception:
    db.rollback()
    raise

finally:
    db.close()
