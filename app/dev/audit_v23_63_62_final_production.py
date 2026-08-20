import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "products.db"

HISTORY_IDS = [
    17, 251,
    19, 168, 321,
    71, 166, 247,
    172, 178, 246, 296, 446,
    445,
]

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

db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True,
)

db.row_factory = sqlite3.Row

errors = []

print("=" * 130)
print("V23.63.62 FINAL PRODUCTION AUDIT")
print("READ ONLY")
print("=" * 130)


# ============================================================
# 1. GLOBAL INTEGRITY
# ============================================================

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


print()
print("GLOBAL INTEGRITY")
print("-" * 130)

for key, value in checks.items():

    ok = value == 0

    print(
        "{:<34} {} {}".format(
            key,
            value,
            "PASS" if ok else "FAIL",
        )
    )

    if not ok:
        errors.append(
            "{}={}".format(
                key,
                value,
            )
        )


# ============================================================
# 2. EXACT HISTORY TARGET VERIFICATION
# ============================================================

print()
print("HISTORY TARGET VERIFICATION")
print("-" * 130)

history_verified = 0

for history_id in HISTORY_IDS:

    r = db.execute("""
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

    if r is None:

        print(
            "H{} => FAIL missing".format(
                history_id
            )
        )

        errors.append(
            "H{} missing".format(
                history_id
            )
        )

        continue

    variant_owner = db.execute("""
        SELECT global_product_id
        FROM global_product_variants
        WHERE id=?
    """, (
        r["history_variant"],
    )).fetchone()

    ok = (
        r["history_gp"] == r["offer_gp"]
        and
        r["history_variant"] == r["offer_variant"]
        and
        r["offer_gp"] == r["raw_gp"]
        and
        r["offer_variant"] == r["raw_variant"]
        and
        variant_owner is not None
        and
        variant_owner[0] == r["history_gp"]
    )

    print(
        "H{} O{} RAW{} GP={} V={} => {}".format(
            history_id,
            r["global_offer_id"],
            r["raw_product_id"],
            r["history_gp"],
            r["history_variant"],
            "PASS" if ok else "FAIL",
        )
    )

    if ok:
        history_verified += 1
    else:
        errors.append(
            "H{} chain mismatch".format(
                history_id
            )
        )


# ============================================================
# 3. RAW COUNTER EXACT VERIFICATION
# ============================================================

print()
print("RAW COUNTER TARGETS")
print("-" * 130)

raw_verified = 0

for gp_id in RAW_COUNTER_GPS:

    r = db.execute("""
        SELECT
            gp.raw_product_count AS stored,

            (
                SELECT COUNT(*)
                FROM raw_products rp
                WHERE rp.global_product_id=gp.id
            ) AS actual

        FROM global_products gp
        WHERE gp.id=?
    """, (gp_id,)).fetchone()

    if r is None:

        print(
            "GP{} => FAIL missing".format(
                gp_id
            )
        )

        errors.append(
            "GP{} missing raw counter".format(
                gp_id
            )
        )

        continue

    ok = (
        r["stored"] == r["actual"]
    )

    print(
        "GP{} stored={} actual={} => {}".format(
            gp_id,
            r["stored"],
            r["actual"],
            "PASS" if ok else "FAIL",
        )
    )

    if ok:
        raw_verified += 1
    else:
        errors.append(
            "GP{} raw counter".format(
                gp_id
            )
        )


# ============================================================
# 4. OFFER COUNTER EXACT VERIFICATION
# ============================================================

print()
print("OFFER COUNTER TARGETS")
print("-" * 130)

offer_verified = 0

for gp_id in OFFER_COUNTER_GPS:

    r = db.execute("""
        SELECT
            gp.active_offer_count AS stored,

            (
                SELECT COUNT(*)
                FROM global_offers go
                WHERE go.global_product_id=gp.id
                  AND go.is_active=1
                  AND go.is_hidden=0
                  AND go.lifecycle_status='ACTIVE'
                  AND go.current_price>0
            ) AS actual

        FROM global_products gp
        WHERE gp.id=?
    """, (gp_id,)).fetchone()

    if r is None:

        print(
            "GP{} => FAIL missing".format(
                gp_id
            )
        )

        errors.append(
            "GP{} missing offer counter".format(
                gp_id
            )
        )

        continue

    ok = (
        r["stored"] == r["actual"]
    )

    print(
        "GP{} stored={} actual={} => {}".format(
            gp_id,
            r["stored"],
            r["actual"],
            "PASS" if ok else "FAIL",
        )
    )

    if ok:
        offer_verified += 1
    else:
        errors.append(
            "GP{} offer counter".format(
                gp_id
            )
        )


# ============================================================
# 5. SQLite integrity
# ============================================================

sqlite_integrity = db.execute(
    "PRAGMA integrity_check"
).fetchone()[0]

print()
print(
    "SQLITE INTEGRITY:",
    sqlite_integrity
)

if sqlite_integrity != "ok":
    errors.append(
        "sqlite integrity={}".format(
            sqlite_integrity
        )
    )

db.close()


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 130)
print("FINAL RESULT")
print("=" * 130)

print(
    "HISTORY VERIFIED:",
    history_verified,
    "/",
    len(HISTORY_IDS),
)

print(
    "RAW COUNTERS VERIFIED:",
    raw_verified,
    "/",
    len(RAW_COUNTER_GPS),
)

print(
    "OFFER COUNTERS VERIFIED:",
    offer_verified,
    "/",
    len(OFFER_COUNTER_GPS),
)

print(
    "ERRORS:",
    len(errors)
)

if errors:

    for error in errors:
        print(
            "ERROR:",
            error
        )

    raise SystemExit(1)

print()
print(
    "V23.63.62 FINAL PRODUCTION AUDIT PASS"
)

print(
    "ALL KNOWN PRODUCTION INTEGRITY DEBT = 0"
)

print(
    "REAL DATABASE UNCHANGED"
)
