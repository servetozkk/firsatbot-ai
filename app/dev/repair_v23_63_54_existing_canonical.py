
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DB = ROOT / "data" / "products.db"

SAFE_RELINK = {
    16:  (15, 51, 52, 1),
    29:  (28, 173, 214, 1),
    47:  (46, 155, 193, 2),
    81:  (76, 76, 130, 1),
    82:  (77, 78, 134, 1),
    157: (129, 159, 197, 1),
    158: (130, 157, 195, 1),
    159: (131, 158, 196, 1),
    169: (138, 16, 17, 5),
    172: (140, 140, 171, 1),
    175: (142, 148, 183, 1),
    182: (141, 141, 173, 1),
    185: (144, 144, 178, 1),
    186: (147, 147, 181, 1),
    190: (152, 68, 71, 1),
    191: (153, 120, 146, 2),
    194: (156, 22, 200, 1),
    204: (163, 18, 19, 1),
    211: (170, 173, 214, 3),
    222: (29, 29, 30, 4),
}

SAFE_DELETE = (161, 165, 166, 167, 184, 208)
PRESERVE = (18, 27, 154, 155, 170, 188)
STALE_GPS = (77, 129, 130, 131, 170)

def all_variant_fk_refs(db, variant_id):
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

db = sqlite3.connect(str(DB))
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys=ON")

try:
    db.execute("BEGIN IMMEDIATE")

    # V23.63.54: pre-existing historical wrong-GP rows are
    # preserved, but this repair may not create new ones.
    history_wrong_gp_before = {
        row["id"]
        for row in db.execute(
            """
            SELECT h.id
            FROM global_offer_price_history h
            JOIN global_product_variants gv
              ON gv.id=h.global_variant_id
            WHERE h.global_variant_id IS NOT NULL
              AND h.global_product_id != gv.global_product_id
            """
        ).fetchall()
    }

    # ------------------------------------------------------------
    # A) Snapshot PRESERVE rows so any accidental mutation rolls back.
    # ------------------------------------------------------------
    preserve_snapshot = {}
    for vid in PRESERVE:
        row = db.execute(
            """
            SELECT id,global_product_id,variant_key,color,network,model_code
            FROM global_product_variants
            WHERE id=?
            """,
            (vid,),
        ).fetchone()

        if row is None:
            raise RuntimeError("PRESERVE variant {} missing".format(vid))

        preserve_snapshot[vid] = tuple(row)

    # ------------------------------------------------------------
    # B) SAFE_RELINK:
    # Revalidate every source variant and every history row against
    # current global_offer/raw ownership before writing.
    # ------------------------------------------------------------
    relinked = []

    for source_vid, plan in SAFE_RELINK.items():
        source_gp, target_gp, target_vid, expected_history = plan

        source = db.execute(
            """
            SELECT id,global_product_id,variant_key
            FROM global_product_variants
            WHERE id=?
            """,
            (source_vid,),
        ).fetchone()

        if source is None:
            raise RuntimeError("SAFE_RELINK source V{} missing".format(source_vid))

        if source["global_product_id"] != source_gp:
            raise RuntimeError(
                "SAFE_RELINK V{} source GP mismatch {} != {}".format(
                    source_vid, source["global_product_id"], source_gp
                )
            )

        target = db.execute(
            """
            SELECT id,global_product_id
            FROM global_product_variants
            WHERE id=?
            """,
            (target_vid,),
        ).fetchone()

        if target is None or target["global_product_id"] != target_gp:
            raise RuntimeError(
                "SAFE_RELINK V{} target GP/V invalid".format(source_vid)
            )

        direct_raw = db.execute(
            "SELECT COUNT(*) FROM raw_products WHERE global_variant_id=?",
            (source_vid,),
        ).fetchone()[0]

        direct_offer = db.execute(
            "SELECT COUNT(*) FROM global_offers WHERE global_variant_id=?",
            (source_vid,),
        ).fetchone()[0]

        if direct_raw != 0 or direct_offer != 0:
            raise RuntimeError(
                "SAFE_RELINK V{} became live raw={} offer={}".format(
                    source_vid, direct_raw, direct_offer
                )
            )

        history_rows = db.execute(
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

        if len(history_rows) != expected_history:
            raise RuntimeError(
                "SAFE_RELINK V{} history count {} != {}".format(
                    source_vid, len(history_rows), expected_history
                )
            )

        for h in history_rows:
            if not (
                h["offer_gp"] == target_gp
                and h["offer_variant"] == target_vid
                and h["raw_gp"] == target_gp
                and h["raw_variant"] == target_vid
            ):
                raise RuntimeError(
                    "SAFE_RELINK V{} ownership drift H{}: "
                    "offer=GP{}/V{} raw=GP{}/V{} expected=GP{}/V{}".format(
                        source_vid,
                        h["id"],
                        h["offer_gp"],
                        h["offer_variant"],
                        h["raw_gp"],
                        h["raw_variant"],
                        target_gp,
                        target_vid,
                    )
                )

        changed = db.execute(
            """
            UPDATE global_offer_price_history
            SET global_product_id=?,
                global_variant_id=?
            WHERE global_variant_id=?
            """,
            (target_gp, target_vid, source_vid),
        ).rowcount

        if changed != expected_history:
            raise RuntimeError(
                "SAFE_RELINK V{} changed {} != {}".format(
                    source_vid, changed, expected_history
                )
            )

        remaining_refs = [
            x for x in all_variant_fk_refs(db, source_vid)
            if x[2] != 0
        ]

        if remaining_refs:
            raise RuntimeError(
                "SAFE_RELINK V{} FK refs remain {}".format(
                    source_vid, remaining_refs
                )
            )

        deleted = db.execute(
            "DELETE FROM global_product_variants WHERE id=?",
            (source_vid,),
        ).rowcount

        if deleted != 1:
            raise RuntimeError(
                "SAFE_RELINK V{} delete count={}".format(
                    source_vid, deleted
                )
            )

        relinked.append(
            (source_vid, source_gp, target_gp, target_vid, changed)
        )

    # ------------------------------------------------------------
    # C) SAFE_DELETE: no raw/offer/history/other FK refs allowed.
    # ------------------------------------------------------------
    deleted_orphans = []

    for vid in SAFE_DELETE:
        row = db.execute(
            """
            SELECT id,global_product_id,variant_key
            FROM global_product_variants
            WHERE id=?
            """,
            (vid,),
        ).fetchone()

        if row is None:
            raise RuntimeError("SAFE_DELETE V{} missing".format(vid))

        refs = [
            x for x in all_variant_fk_refs(db, vid)
            if x[2] != 0
        ]

        if refs:
            raise RuntimeError(
                "SAFE_DELETE V{} unexpectedly referenced {}".format(
                    vid, refs
                )
            )

        deleted = db.execute(
            "DELETE FROM global_product_variants WHERE id=?",
            (vid,),
        ).rowcount

        if deleted != 1:
            raise RuntimeError(
                "SAFE_DELETE V{} delete count={}".format(
                    vid, deleted
                )
            )

        deleted_orphans.append((vid, row["global_product_id"]))

    # ------------------------------------------------------------
    # D) Retire only audited stale ACTIVE GPs after all ownership
    # and child references have become zero.
    # ------------------------------------------------------------
    retired = []

    for gp_id in STALE_GPS:
        gp = db.execute(
            """
            SELECT id,status
            FROM global_products
            WHERE id=?
            """,
            (gp_id,),
        ).fetchone()

        if gp is None:
            raise RuntimeError("STALE GP{} missing".format(gp_id))

        raw_count = db.execute(
            "SELECT COUNT(*) FROM raw_products WHERE global_product_id=?",
            (gp_id,),
        ).fetchone()[0]

        offer_count = db.execute(
            "SELECT COUNT(*) FROM global_offers WHERE global_product_id=?",
            (gp_id,),
        ).fetchone()[0]

        variant_count = db.execute(
            "SELECT COUNT(*) FROM global_product_variants WHERE global_product_id=?",
            (gp_id,),
        ).fetchone()[0]

        history_count = db.execute(
            "SELECT COUNT(*) FROM global_offer_price_history WHERE global_product_id=?",
            (gp_id,),
        ).fetchone()[0]

        if (raw_count, offer_count, variant_count, history_count) != (0, 0, 0, 0):
            raise RuntimeError(
                "STALE GP{} not empty raw={} offer={} variant={} history={}".format(
                    gp_id, raw_count, offer_count, variant_count, history_count
                )
            )

        db.execute(
            """
            UPDATE global_products
            SET status='RETIRED',
                raw_product_count=0,
                active_offer_count=0,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (gp_id,),
        )

        retired.append(gp_id)

    # ------------------------------------------------------------
    # E) PRESERVE variants must be byte-equivalent on selected fields.
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

    # ------------------------------------------------------------
    # F) Authoritative counters.
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
    # G) Full integrity gate.
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

    history_wrong_gp_after = {
        row["id"]
        for row in db.execute(
            """
            SELECT h.id
            FROM global_offer_price_history h
            JOIN global_product_variants gv
              ON gv.id=h.global_variant_id
            WHERE h.global_variant_id IS NOT NULL
              AND h.global_product_id != gv.global_product_id
            """
        ).fetchall()
    }

    new_history_wrong_gp = (
        history_wrong_gp_after
        - history_wrong_gp_before
    )

    checks["history_variant_wrong_gp_new"] = len(
        new_history_wrong_gp
    )

    if new_history_wrong_gp:
        raise RuntimeError(
            "New history wrong-GP rows created: {}".format(
                sorted(new_history_wrong_gp)
            )
        )

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

    checks["safe_relink_source_remaining"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_product_variants
        WHERE id IN (
            16,29,47,81,82,157,158,159,169,172,
            175,182,185,186,190,191,194,204,211,222
        )
        """
    ).fetchone()[0]

    checks["safe_relink_history_remaining"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_offer_price_history
        WHERE global_variant_id IN (
            16,29,47,81,82,157,158,159,169,172,
            175,182,185,186,190,191,194,204,211,222
        )
        """
    ).fetchone()[0]

    checks["safe_delete_remaining"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_product_variants
        WHERE id IN (161,165,166,167,184,208)
        """
    ).fetchone()[0]

    checks["stale_active_remaining"] = db.execute(
        """
        SELECT COUNT(*)
        FROM global_products
        WHERE id IN (77,129,130,131,170)
          AND status='ACTIVE'
        """
    ).fetchone()[0]

    if any(checks.values()):
        raise RuntimeError(
            "Post-repair integrity failure: {}".format(checks)
        )

    db.commit()

    print(
        "V23.63.54 repair OK: "
        "relinked={}; safe_deleted={}; retired={}; "
        "preserved={}; integrity={}".format(
            relinked,
            deleted_orphans,
            retired,
            list(PRESERVE),
            checks,
        )
    )

except Exception:
    db.rollback()
    raise

finally:
    db.close()
