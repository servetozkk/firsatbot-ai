import argparse
import shutil
import sqlite3
from datetime import datetime
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

EXPECTED_BASELINE = {
    "history_wrong_gp": 14,
    "active_variant_drift": 0,
    "offer_variant_wrong_gp": 0,
    "raw_variant_wrong_gp": 0,
    "raw_counter": 6,
    "offer_counter": 4,
    "duplicate_active_identity_keys": 0,
}

EXPECTED_POST = {
    "history_wrong_gp": 0,
    "active_variant_drift": 0,
    "offer_variant_wrong_gp": 0,
    "raw_variant_wrong_gp": 0,
    "raw_counter": 0,
    "offer_counter": 0,
    "duplicate_active_identity_keys": 0,
}


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


def run_preflight():

    db = sqlite3.connect(
        "file:" + str(DB).replace("\\", "/") + "?mode=ro",
        uri=True,
    )

    db.row_factory = sqlite3.Row

    print("=" * 130)
    print("V23.63.62 PRODUCTION DEBT REPAIR PREFLIGHT")
    print("REAL DB - READ ONLY")
    print("=" * 130)

    snapshot = integrity_snapshot(db)

    print()
    print("BASELINE:", snapshot)

    errors = []

    if snapshot != EXPECTED_BASELINE:
        errors.append(
            "baseline mismatch {}".format(snapshot)
        )

    print()
    print("HISTORY TARGETS")

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
            errors.append(
                "H{} missing".format(history_id)
            )
            print(
                "H{} => FAIL missing".format(history_id)
            )
            continue

        variant_owner = db.execute("""
            SELECT global_product_id
            FROM global_product_variants
            WHERE id=?
        """, (
            row["offer_variant"],
        )).fetchone()

        safe = (
            row["offer_gp"] == row["raw_gp"]
            and row["offer_variant"] == row["raw_variant"]
            and variant_owner is not None
            and variant_owner[0] == row["offer_gp"]
            and row["history_gp"] != row["offer_gp"]
        )

        print(
            "H{} O{} RAW{} {} -> {} => {}".format(
                history_id,
                row["global_offer_id"],
                row["raw_product_id"],
                row["history_gp"],
                row["offer_gp"],
                "PASS" if safe else "FAIL",
            )
        )

        if not safe:
            errors.append(
                "H{} chain unsafe".format(history_id)
            )

    db.close()

    print()
    print("ERRORS:", len(errors))

    if errors:
        for error in errors:
            print("FAIL:", error)

        raise SystemExit(1)

    print(
        "V23.63.62 PRODUCTION PREFLIGHT PASS"
    )
    print(
        "REAL DATABASE UNCHANGED"
    )


def create_backup():

    stamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    backup = (
        DB.parent
        / "products.v236362-before-debt-repair-{}.db".format(
            stamp
        )
    )

    shutil.copy2(
        DB,
        backup,
    )

    test = sqlite3.connect(
        "file:" + str(backup).replace("\\", "/") + "?mode=ro",
        uri=True,
    )

    result = test.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    test.close()

    if result != "ok":
        backup.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "backup integrity failed {}".format(
                result
            )
        )

    return backup


def run_apply():

    print("=" * 130)
    print("V23.63.62 PRODUCTION DEBT REPAIR APPLY")
    print("=" * 130)

    run_preflight()

    backup = create_backup()

    print()
    print(
        "BACKUP:",
        backup
    )

    db = sqlite3.connect(
        str(DB)
    )

    db.row_factory = sqlite3.Row

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
                    "H{} missing".format(
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

            if not (
                row["offer_gp"] == row["raw_gp"]
                and row["offer_variant"] == row["raw_variant"]
                and variant_owner is not None
                and variant_owner[0] == row["offer_gp"]
                and row["history_gp"] != row["offer_gp"]
            ):
                raise RuntimeError(
                    "H{} chain drift before write".format(
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
                    "H{} rowcount={}".format(
                        history_id,
                        cur.rowcount,
                    )
                )

            history_updated += 1


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


        post = integrity_snapshot(
            db
        )

        print()
        print(
            "POST INTEGRITY:",
            post
        )

        if post != EXPECTED_POST:
            raise RuntimeError(
                "post integrity failure {}".format(
                    post
                )
            )


        # Exact target verification.
        target_placeholders = ",".join(
            "?"
            for _ in HISTORY_IDS
        )

        remaining = db.execute("""
            SELECT COUNT(*)
            FROM global_offer_price_history h
            JOIN global_offers go
              ON go.id=h.global_offer_id
            WHERE h.id IN ({})
              AND (
                  h.global_product_id != go.global_product_id
                  OR
                  h.global_variant_id != go.global_variant_id
              )
        """.format(
            target_placeholders
        ), HISTORY_IDS).fetchone()[0]

        if remaining != 0:
            raise RuntimeError(
                "history verifier remaining={}".format(
                    remaining
                )
            )


        db.commit()

        print()
        print(
            "V23.63.62 PRODUCTION DEBT REPAIR COMMIT OK"
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

        print(
            "BACKUP:",
            backup
        )

    except Exception:

        db.rollback()

        print()
        print(
            "V23.63.62 PRODUCTION DEBT REPAIR ROLLBACK"
        )

        print(
            "BACKUP PRESERVED:",
            backup
        )

        raise

    finally:
        db.close()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--preflight",
        action="store_true",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    if args.preflight and args.apply:
        raise SystemExit(
            "Use only one mode."
        )

    if args.preflight:
        run_preflight()
        return

    if args.apply:
        run_apply()
        return

    raise SystemExit(
        "Use --preflight or --apply."
    )


if __name__ == "__main__":
    main()
