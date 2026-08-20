import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REAL_DB = ROOT / "data" / "products.db"

PREVIEW_DB = (
    ROOT
    / "data"
    / "_v236362_existing_debt_preview.db"
)

# ------------------------------------------------------------
# Build isolated preview copy
# ------------------------------------------------------------

if PREVIEW_DB.exists():
    PREVIEW_DB.unlink()

shutil.copy2(
    REAL_DB,
    PREVIEW_DB,
)

db = sqlite3.connect(
    str(PREVIEW_DB)
)

db.row_factory = sqlite3.Row

print("=" * 130)
print("V23.63.62 EXISTING DEBT REPAIR PREVIEW")
print("COPY DB ONLY")
print("=" * 130)

# ------------------------------------------------------------
# Baseline snapshot
# ------------------------------------------------------------

def integrity_snapshot(db):

    checks = {}

    checks["history_wrong_gp"] = db.execute("""
        SELECT COUNT(*)
        FROM global_offer_price_history h
        JOIN global_product_variants gv
          ON gv.id=h.global_variant_id
        WHERE h.global_variant_id IS NOT NULL
          AND h.global_product_id != gv.global_product_id
    """).fetchone()[0]

    checks["active_variant_drift"] = db.execute("""
        SELECT COUNT(*)
        FROM global_offers go
        JOIN raw_products rp
          ON rp.id=go.raw_product_id
        WHERE go.is_active=1
          AND go.is_hidden=0
          AND go.lifecycle_status='ACTIVE'
          AND go.current_price>0
          AND go.global_variant_id IS NOT NULL
          AND rp.global_variant_id IS NOT NULL
          AND go.global_variant_id != rp.global_variant_id
    """).fetchone()[0]

    checks["offer_variant_wrong_gp"] = db.execute("""
        SELECT COUNT(*)
        FROM global_offers go
        JOIN global_product_variants gv
          ON gv.id=go.global_variant_id
        WHERE go.global_variant_id IS NOT NULL
          AND go.global_product_id != gv.global_product_id
    """).fetchone()[0]

    checks["raw_variant_wrong_gp"] = db.execute("""
        SELECT COUNT(*)
        FROM raw_products rp
        JOIN global_product_variants gv
          ON gv.id=rp.global_variant_id
        WHERE rp.global_variant_id IS NOT NULL
          AND rp.global_product_id != gv.global_product_id
    """).fetchone()[0]

    checks["raw_counter"] = db.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT gp.id
            FROM global_products gp
            LEFT JOIN raw_products rp
              ON rp.global_product_id=gp.id
            GROUP BY gp.id
            HAVING gp.raw_product_count != COUNT(rp.id)
        )
    """).fetchone()[0]

    checks["offer_counter"] = db.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT gp.id
            FROM global_products gp
            LEFT JOIN global_offers go
              ON go.global_product_id=gp.id
            GROUP BY gp.id
            HAVING gp.active_offer_count !=
                SUM(
                    CASE
                        WHEN go.is_active=1
                         AND go.is_hidden=0
                         AND go.lifecycle_status='ACTIVE'
                         AND go.current_price>0
                        THEN 1
                        ELSE 0
                    END
                )
        )
    """).fetchone()[0]

    checks["duplicate_active_identity_keys"] = db.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT identity_key
            FROM global_products
            WHERE status='ACTIVE'
              AND identity_key IS NOT NULL
              AND identity_key != ''
            GROUP BY identity_key
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    return checks


baseline = integrity_snapshot(db)

print()
print("BASELINE:", baseline)

EXPECTED_BASELINE = {
    "history_wrong_gp": 14,
    "active_variant_drift": 0,
    "offer_variant_wrong_gp": 0,
    "raw_variant_wrong_gp": 0,
    "raw_counter": 6,
    "offer_counter": 4,
    "duplicate_active_identity_keys": 0,
}

if baseline != EXPECTED_BASELINE:
    raise RuntimeError(
        "unexpected preview baseline {}".format(
            baseline
        )
    )


# ------------------------------------------------------------
# Explicit history debt set
# ------------------------------------------------------------

HISTORY_IDS = [
    17,
    251,
    19,
    168,
    321,
    71,
    166,
    247,
    172,
    178,
    246,
    296,
    446,
    445,
]

if len(set(HISTORY_IDS)) != 14:
    raise RuntimeError(
        "history target set invalid"
    )


# ------------------------------------------------------------
# Counter targets
# ------------------------------------------------------------

RAW_COUNTER_GPS = [
    16,
    18,
    68,
    174,
    175,
    185,
]

OFFER_COUNTER_GPS = [
    18,
    68,
    174,
    175,
]


# ------------------------------------------------------------
# Apply preview transaction
# ------------------------------------------------------------

try:
    db.execute(
        "BEGIN IMMEDIATE"
    )

    history_updated = 0

    for history_id in HISTORY_IDS:

        row = db.execute("""
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

            WHERE h.id=?
        """, (history_id,)).fetchone()

        if row is None:
            raise RuntimeError(
                "history H{} missing".format(
                    history_id
                )
            )

        if (
            row["offer_gp"] != row["raw_gp"]
            or
            row["offer_variant"] != row["raw_variant"]
        ):
            raise RuntimeError(
                "history H{} current chain not safe".format(
                    history_id
                )
            )

        variant_owner = db.execute("""
            SELECT global_product_id
            FROM global_product_variants
            WHERE id=?
        """, (
            row["offer_variant"],
        )).fetchone()

        if variant_owner is None:
            raise RuntimeError(
                "history H{} variant missing".format(
                    history_id
                )
            )

        if (
            variant_owner[0]
            != row["offer_gp"]
        ):
            raise RuntimeError(
                "history H{} variant owner mismatch".format(
                    history_id
                )
            )

        cur = db.execute("""
            UPDATE global_offer_price_history
            SET
                global_product_id=?,
                global_variant_id=?
            WHERE id=?
              AND global_product_id=?
        """, (
            row["offer_gp"],
            row["offer_variant"],
            history_id,
            row["history_gp"],
        ))

        if cur.rowcount != 1:
            raise RuntimeError(
                "history H{} update rowcount={}".format(
                    history_id,
                    cur.rowcount,
                )
            )

        history_updated += 1


    # --------------------------------------------------------
    # RAW counter rebuild
    # --------------------------------------------------------

    raw_rebuilt = 0

    for gp_id in RAW_COUNTER_GPS:

        actual = db.execute("""
            SELECT COUNT(*)
            FROM raw_products
            WHERE global_product_id=?
        """, (gp_id,)).fetchone()[0]

        cur = db.execute("""
            UPDATE global_products
            SET raw_product_count=?
            WHERE id=?
        """, (
            actual,
            gp_id,
        ))

        if cur.rowcount != 1:
            raise RuntimeError(
                "raw counter GP{} rowcount={}".format(
                    gp_id,
                    cur.rowcount,
                )
            )

        raw_rebuilt += 1


    # --------------------------------------------------------
    # Offer counter rebuild
    # --------------------------------------------------------

    offer_rebuilt = 0

    for gp_id in OFFER_COUNTER_GPS:

        actual = db.execute("""
            SELECT COUNT(*)
            FROM global_offers
            WHERE global_product_id=?
              AND is_active=1
              AND is_hidden=0
              AND lifecycle_status='ACTIVE'
              AND current_price>0
        """, (gp_id,)).fetchone()[0]

        cur = db.execute("""
            UPDATE global_products
            SET active_offer_count=?
            WHERE id=?
        """, (
            actual,
            gp_id,
        ))

        if cur.rowcount != 1:
            raise RuntimeError(
                "offer counter GP{} rowcount={}".format(
                    gp_id,
                    cur.rowcount,
                )
            )

        offer_rebuilt += 1


    # --------------------------------------------------------
    # Post repair integrity
    # --------------------------------------------------------

    post = integrity_snapshot(db)

    print(
        "POST REPAIR:",
        post
    )

    EXPECTED_POST = {
        "history_wrong_gp": 0,
        "active_variant_drift": 0,
        "offer_variant_wrong_gp": 0,
        "raw_variant_wrong_gp": 0,
        "raw_counter": 0,
        "offer_counter": 0,
        "duplicate_active_identity_keys": 0,
    }

    if post != EXPECTED_POST:
        raise RuntimeError(
            "post repair integrity failed {}".format(
                post
            )
        )


    # --------------------------------------------------------
    # Exact history verifier
    # --------------------------------------------------------

    remaining = db.execute("""
        SELECT COUNT(*)
        FROM global_offer_price_history
        WHERE id IN ({})
          AND global_product_id != (
              SELECT go.global_product_id
              FROM global_offers go
              WHERE go.id=
                    global_offer_price_history.global_offer_id
          )
    """.format(
        ",".join(
            "?"
            for _ in HISTORY_IDS
        )
    ), HISTORY_IDS).fetchone()[0]

    if remaining != 0:
        raise RuntimeError(
            "history target verification failed {}".format(
                remaining
            )
        )


    db.commit()

    print()
    print(
        "V23.63.62 COPY-DB REPAIR PREVIEW PASS"
    )

    print(
        "HISTORY UPDATED:",
        history_updated
    )

    print(
        "RAW COUNTERS REBUILT:",
        raw_rebuilt
    )

    print(
        "OFFER COUNTERS REBUILT:",
        offer_rebuilt
    )

    print(
        "FINAL INTEGRITY:",
        post
    )

except Exception:

    db.rollback()

    print()
    print(
        "V23.63.62 COPY-DB PREVIEW ROLLBACK"
    )

    raise

finally:
    db.close()


# ------------------------------------------------------------
# Real DB immutable verification
# ------------------------------------------------------------

real = sqlite3.connect(
    "file:"
    + str(REAL_DB).replace("\\", "/")
    + "?mode=ro",
    uri=True,
)

real.row_factory = sqlite3.Row

real_history = real.execute("""
    SELECT COUNT(*)
    FROM global_offer_price_history h
    JOIN global_product_variants gv
      ON gv.id=h.global_variant_id
    WHERE h.global_variant_id IS NOT NULL
      AND h.global_product_id != gv.global_product_id
""").fetchone()[0]

real_raw_counter = real.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT gp.id
        FROM global_products gp
        LEFT JOIN raw_products rp
          ON rp.global_product_id=gp.id
        GROUP BY gp.id
        HAVING gp.raw_product_count != COUNT(rp.id)
    )
""").fetchone()[0]

real_offer_counter = real.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT gp.id
        FROM global_products gp
        LEFT JOIN global_offers go
          ON go.global_product_id=gp.id
        GROUP BY gp.id
        HAVING gp.active_offer_count !=
            SUM(
                CASE
                    WHEN go.is_active=1
                     AND go.is_hidden=0
                     AND go.lifecycle_status='ACTIVE'
                     AND go.current_price>0
                    THEN 1
                    ELSE 0
                END
            )
    )
""").fetchone()[0]

real.close()

print()
print(
    "REAL DB BASELINE:",
    {
        "history_wrong_gp": real_history,
        "raw_counter": real_raw_counter,
        "offer_counter": real_offer_counter,
    }
)

if (
    real_history != 14
    or real_raw_counter != 6
    or real_offer_counter != 4
):
    raise RuntimeError(
        "REAL DB baseline changed unexpectedly"
    )

print(
    "REAL DATABASE UNCHANGED"
)

print(
    "PREVIEW DB:",
    PREVIEW_DB
)
