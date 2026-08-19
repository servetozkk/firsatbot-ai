import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "products.db"

EXPECTED_TARGETS = {
    191: [348],
    192: [344],
    193: [345, 346],
    194: [347],
    195: [16, 227, 228],
    196: [226, 229],
    197: [230],
    198: [231],
    199: [321],
    200: [258],
    201: [304],
    202: [333],
}

db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True,
)

db.row_factory = sqlite3.Row

print("=" * 130)
print("V23.63.61 FINAL PRODUCTION AUDIT")
print("READ ONLY")
print("=" * 130)

errors = []

# ------------------------------------------------------------
# Target ownership
# ------------------------------------------------------------

print()
print("TARGET OWNERSHIP")
print("-" * 130)

verified_raws = 0

for gp_id, expected_raws in EXPECTED_TARGETS.items():

    gp = db.execute("""
        SELECT
            id,
            status,
            identity_source,
            raw_product_count
        FROM global_products
        WHERE id=?
    """, (gp_id,)).fetchone()

    actual_raws = [
        r[0]
        for r in db.execute("""
            SELECT id
            FROM raw_products
            WHERE global_product_id=?
            ORDER BY id
        """, (gp_id,)).fetchall()
    ]

    expected = sorted(expected_raws)
    actual = sorted(actual_raws)

    ok = (
        gp is not None
        and gp["status"] == "ACTIVE"
        and (
            gp["identity_source"] or ""
        ).startswith(
            "identity_v236361_contract:"
        )
        and expected == actual
    )

    print(
        "GP{} expected={} actual={} => {}".format(
            gp_id,
            expected,
            actual,
            "PASS" if ok else "FAIL",
        )
    )

    if not ok:
        errors.append(
            "GP{} ownership".format(gp_id)
        )

    verified_raws += len(actual)


# ------------------------------------------------------------
# Critical integrity
# ------------------------------------------------------------

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
print("INTEGRITY")
print("-" * 130)

expected = {
    "history_wrong_gp": 14,
    "active_variant_drift": 0,
    "offer_variant_wrong_gp": 0,
    "raw_variant_wrong_gp": 0,
    "raw_counter": 6,
    "offer_counter": 4,
    "duplicate_active_identity_keys": 0,
}

for key, expected_value in expected.items():

    actual = checks[key]

    ok = actual == expected_value

    print(
        "{:<34} expected={} actual={} {}".format(
            key,
            expected_value,
            actual,
            "PASS" if ok else "FAIL",
        )
    )

    if not ok:
        errors.append(
            "{} expected={} actual={}".format(
                key,
                expected_value,
                actual,
            )
        )


# ------------------------------------------------------------
# Contract referential integrity
# ------------------------------------------------------------

contract_variant_errors = db.execute("""
    SELECT COUNT(*)
    FROM raw_products rp
    JOIN global_products gp
      ON gp.id=rp.global_product_id
    JOIN global_product_variants gv
      ON gv.id=rp.global_variant_id
    WHERE gp.identity_source LIKE 'identity_v236361_contract:%'
      AND gv.global_product_id != rp.global_product_id
""").fetchone()[0]

print()
print(
    "CONTRACT VARIANT ERRORS:",
    contract_variant_errors
)

if contract_variant_errors:
    errors.append(
        "contract variant ownership"
    )


db.close()

print()
print("=" * 130)
print("FINAL RESULT")
print("=" * 130)

print("TARGET GPS:", len(EXPECTED_TARGETS))
print("VERIFIED RAWS:", verified_raws)
print("ERRORS:", len(errors))

if errors:
    for error in errors:
        print("ERROR:", error)

    raise SystemExit(1)

print()
print("V23.63.61 FINAL PRODUCTION AUDIT PASS")
print("REAL DATABASE UNCHANGED")
