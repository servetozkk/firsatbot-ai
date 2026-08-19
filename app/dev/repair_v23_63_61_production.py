
import argparse
import hashlib
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
DB = ROOT / "data" / "products.db"

# ============================================================
# V23.63.61 production repair contracts
#
# PRELIGHT ONLY FOR NOW.
# No DB writes are executed unless a future --apply mode is added.
# ============================================================

CONTRACTS = [
    {
        "source_gp": 12,
        "raws": [348],
        "expected_variants": {348: 13},
        "brand": "attack shark",
        "family": "x11 se",
        "model_code": "x11se",
        "ram": None,
        "storage": None,
    },
    {
        "source_gp": 29,
        "raws": [344],
        "expected_variants": {344: 30},
        "brand": "casper",
        "family": "nirvana s100",
        "model_code": "s100.1342-bf00x-g-f",
        "ram": 16,
        "storage": 1024,
    },
    {
        "source_gp": 29,
        "raws": [345, 346],
        "expected_variants": {345: 30, 346: 30},
        "brand": "casper",
        "family": "nirvana s100",
        "model_code": "s100.1362-cf00x-g-f",
        "ram": 24,
        "storage": 1024,
    },
    {
        "source_gp": 29,
        "raws": [347],
        "expected_variants": {347: 30},
        "brand": "casper",
        "family": "nirvana s100",
        "model_code": None,
        "ram": 16,
        "storage": 500,
    },
    {
        "source_gp": 51,
        "raws": [16, 227, 228],
        "expected_variants": {16: 52, 227: 52, 228: 52},
        "brand": "monster",
        "family": "abra a7 v15.6.4",
        "model_code": "v15.6.4",
        "ram": 16,
        "storage": 1024,
    },
    {
        "source_gp": 51,
        "raws": [226, 229],
        "expected_variants": {226: 52, 229: 52},
        "brand": "monster",
        "family": "abra a5 v21.8.5",
        "model_code": "v21.8.5",
        "ram": 32,
        "storage": 1024,
    },
    {
        "source_gp": 120,
        "raws": [230],
        "expected_variants": {230: 146},
        "brand": "lenovo",
        "family": "loq 15arp10e",
        "model_code": "83s00030trat37",
        "ram": 16,
        "storage": 512,
    },
    {
        "source_gp": 120,
        "raws": [231],
        "expected_variants": {231: 146},
        "brand": "lenovo",
        "family": "loq",
        "model_code": "83jc000qtra29",
        "ram": 16,
        "storage": 2048,
    },
    {
        "source_gp": 134,
        "raws": [321],
        "expected_variants": {321: 164},
        "brand": "apple",
        "family": "ipad a16",
        "model_code": "md4d4tu/a",
        "ram": 8,
        "storage": 128,
    },
    {
        "source_gp": 154,
        "raws": [258],
        "expected_variants": {258: 192},
        "brand": "lenovo",
        "family": "ideapad slim 3",
        "model_code": None,
        "ram": 8,
        "storage": 512,
    },
    {
        "source_gp": 160,
        "raws": [304],
        "expected_variants": {304: 199},
        "brand": "huawei",
        "family": "watch d2 + freebuds se 2 bundle",
        "model_code": None,
        "ram": None,
        "storage": None,
    },
    {
        "source_gp": 173,
        "raws": [333],
        "expected_variants": {333: 214},
        "brand": "xaser",
        "family": "sword x60",
        "model_code": "hsr001362",
        "ram": 32,
        "storage": 1024,
    },
]


EXPECTED_BASELINE = {
    # Existing production debt measured immediately before
    # V23.63.61 repair. These may remain but MUST NOT worsen.
    "history_wrong_gp": 14,
    "active_variant_drift": 0,
    "offer_variant_wrong_gp": 0,
    "raw_variant_wrong_gp": 0,
    "raw_counter": 6,
    "offer_counter": 4,
    "duplicate_active_identity_keys": 0,
}


def count_raw_counter_mismatch(db):

    return db.execute("""
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.raw_product_count != (
            SELECT COUNT(*)
            FROM raw_products rp
            WHERE rp.global_product_id=gp.id
        )
    """).fetchone()[0]


def count_offer_counter_mismatch(db):

    return db.execute("""
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
    """).fetchone()[0]


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

    checks["raw_counter"] = (
        count_raw_counter_mismatch(db)
    )

    checks["offer_counter"] = (
        count_offer_counter_mismatch(db)
    )

    checks["duplicate_active_identity_keys"] = db.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT
                identity_key,
                COUNT(*) AS c
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

    errors = []

    print("=" * 130)
    print("V23.63.61 PRODUCTION REPAIR PREFLIGHT")
    print("REAL DB - READ ONLY")
    print("=" * 130)

    print()
    print("DATABASE:", DB)

    # --------------------------------------------------------
    # Contract ownership assertions
    # --------------------------------------------------------

    print()
    print("=" * 130)
    print("CONTRACT OWNERSHIP")
    print("=" * 130)

    seen_raws = set()

    for contract in CONTRACTS:

        source_gp = contract["source_gp"]

        for raw_id in contract["raws"]:

            if raw_id in seen_raws:
                errors.append(
                    "RAW{} appears in multiple contracts".format(
                        raw_id
                    )
                )

            seen_raws.add(raw_id)

            row = db.execute("""
                SELECT
                    id,
                    store_code,
                    title_raw,
                    global_product_id,
                    global_variant_id,
                    reconciliation_status
                FROM raw_products
                WHERE id=?
            """, (raw_id,)).fetchone()

            if row is None:
                errors.append(
                    "RAW{} missing".format(
                        raw_id
                    )
                )
                print(
                    "RAW{} MISSING".format(
                        raw_id
                    )
                )
                continue

            expected_variant = (
                contract["expected_variants"]
                .get(raw_id)
            )

            ok = True

            if row["global_product_id"] != source_gp:
                ok = False
                errors.append(
                    "RAW{} GP expected={} actual={}".format(
                        raw_id,
                        source_gp,
                        row["global_product_id"],
                    )
                )

            if row["global_variant_id"] != expected_variant:
                ok = False
                errors.append(
                    "RAW{} variant expected={} actual={}".format(
                        raw_id,
                        expected_variant,
                        row["global_variant_id"],
                    )
                )

            offers = db.execute("""
                SELECT
                    id,
                    global_product_id,
                    global_variant_id,
                    lifecycle_status,
                    is_active,
                    is_hidden,
                    current_price
                FROM global_offers
                WHERE raw_product_id=?
                ORDER BY id
            """, (raw_id,)).fetchall()

            if len(offers) != 1:
                ok = False
                errors.append(
                    "RAW{} expected exactly 1 offer got {}".format(
                        raw_id,
                        len(offers),
                    )
                )

            elif offers[0]["global_product_id"] != source_gp:
                ok = False
                errors.append(
                    "RAW{} offer GP expected={} actual={}".format(
                        raw_id,
                        source_gp,
                        offers[0]["global_product_id"],
                    )
                )

            print(
                "RAW{} GP={} V={} OFFER={} STATUS={} => {}".format(
                    raw_id,
                    row["global_product_id"],
                    row["global_variant_id"],
                    offers[0]["id"]
                    if len(offers) == 1
                    else None,
                    row["reconciliation_status"],
                    "PASS" if ok else "FAIL",
                )
            )

    print()
    print(
        "TOTAL CONTRACT RAWS:",
        len(seen_raws)
    )

    # --------------------------------------------------------
    # Baseline integrity assertions
    # --------------------------------------------------------

    print()
    print("=" * 130)
    print("BASELINE INTEGRITY")
    print("=" * 130)

    snapshot = integrity_snapshot(
        db
    )

    for key in EXPECTED_BASELINE:

        actual = snapshot[key]
        expected = EXPECTED_BASELINE[key]

        status = (
            "PASS"
            if actual == expected
            else "FAIL"
        )

        print(
            "{:<34} expected={} actual={} {}".format(
                key,
                expected,
                actual,
                status,
            )
        )

        if actual != expected:
            errors.append(
                "baseline {} expected={} actual={}".format(
                    key,
                    expected,
                    actual,
                )
            )

    # --------------------------------------------------------
    # Existing target-contract namespace must not already exist
    # --------------------------------------------------------

    existing_contract_targets = db.execute("""
        SELECT
            id,
            identity_source
        FROM global_products
        WHERE identity_source LIKE
              'identity_v236361_contract:%'
        ORDER BY id
    """).fetchall()

    print()
    print("=" * 130)
    print("CONTRACT NAMESPACE")
    print("=" * 130)

    print(
        "EXISTING TARGET COUNT:",
        len(existing_contract_targets)
    )

    if existing_contract_targets:

        for row in existing_contract_targets:
            print(
                "GP{} {}".format(
                    row["id"],
                    row["identity_source"],
                )
            )

        errors.append(
            "production DB already contains v236361 contract target(s)"
        )

    db.close()

    print()
    print("=" * 130)
    print("PREFLIGHT RESULT")
    print("=" * 130)

    print(
        "ERRORS:",
        len(errors)
    )

    if errors:

        for error in errors:
            print(
                "FAIL:",
                error
            )

        raise SystemExit(1)

    print(
        "V23.63.61 PRODUCTION PREFLIGHT PASS"
    )

    print(
        "REAL DATABASE UNCHANGED"
    )



def table_columns(db, table):
    return {
        r[1]
        for r in db.execute(
            "PRAGMA table_info({})".format(table)
        )
    }


def clone_variant(db, source_variant_id, target_gp):
    if source_variant_id is None:
        return None

    source = db.execute("""
        SELECT *
        FROM global_product_variants
        WHERE id=?
    """, (source_variant_id,)).fetchone()

    if source is None:
        raise RuntimeError(
            "source variant {} missing".format(source_variant_id)
        )

    names = []
    values = []

    for name in source.keys():
        if name == "id":
            continue

        names.append(name)

        if name == "global_product_id":
            values.append(target_gp)
        else:
            values.append(source[name])

    placeholders = ",".join("?" for _ in names)

    db.execute(
        "INSERT INTO global_product_variants ({}) VALUES ({})".format(
            ",".join(names),
            placeholders,
        ),
        values,
    )

    return db.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]


def rebuild_counter(db, gp_id):
    raw_count = db.execute("""
        SELECT COUNT(*)
        FROM raw_products
        WHERE global_product_id=?
    """, (gp_id,)).fetchone()[0]

    offer_count = db.execute("""
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
        SET raw_product_count=?,
            active_offer_count=?
        WHERE id=?
    """, (
        raw_count,
        offer_count,
        gp_id,
    ))

    if cur.rowcount != 1:
        raise RuntimeError(
            "counter rebuild failed GP{}".format(gp_id)
        )


def create_backup():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    backup = (
        DB.parent
        / "products.v236361-before-repair-{}.db".format(stamp)
    )

    shutil.copy2(DB, backup)

    test = sqlite3.connect(
        "file:" + str(backup).replace("\\", "/") + "?mode=ro",
        uri=True,
    )

    result = test.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    test.close()

    if result != "ok":
        backup.unlink(missing_ok=True)
        raise RuntimeError(
            "backup integrity failure: {}".format(result)
        )

    return backup


def create_target_gp(db, contract, seed, source_gp):
    source_gp_row = db.execute("""
        SELECT *
        FROM global_products
        WHERE id=?
    """, (source_gp,)).fetchone()

    if source_gp_row is None:
        raise RuntimeError(
            "source GP{} missing".format(source_gp)
        )

    identity_source = (
        "identity_v236361_contract:"
        "brand={}|family={}|ram={}|storage={}|model_code={}"
    ).format(
        contract["brand"] or "",
        contract["family"] or "",
        contract["ram"] if contract["ram"] is not None else "",
        contract["storage"] if contract["storage"] is not None else "",
        contract["model_code"] or "",
    )

    identity_key = hashlib.md5(
        identity_source.encode("utf-8")
    ).hexdigest()

    overrides = {
        "canonical_name": seed["title_raw"],
        "normalized_brand": contract["brand"],
        "family": contract["family"],
        "ram_gb": contract["ram"],
        "storage_gb": contract["storage"],
        "model_code": contract["model_code"],
        "status": "ACTIVE",
        "raw_product_count": 0,
        "active_offer_count": 0,
        "identity_source": identity_source,
        "identity_key": identity_key,
    }

    names = []
    values = []

    for name in source_gp_row.keys():
        if name == "id":
            continue

        names.append(name)

        values.append(
            overrides[name]
            if name in overrides
            else source_gp_row[name]
        )

    placeholders = ",".join("?" for _ in names)

    db.execute(
        "INSERT INTO global_products ({}) VALUES ({})".format(
            ",".join(names),
            placeholders,
        ),
        values,
    )

    return (
        db.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0],
        identity_source,
    )


def run_apply():
    print("=" * 130)
    print("V23.63.61 PRODUCTION REPAIR APPLY")
    print("=" * 130)

    # Preflight must still pass immediately before write.
    run_preflight()

    backup = create_backup()

    print()
    print("BACKUP:", backup)

    db = sqlite3.connect(str(DB))
    db.row_factory = sqlite3.Row

    created = []

    try:
        db.execute("BEGIN IMMEDIATE")

        for contract in CONTRACTS:
            source_gp = contract["source_gp"]

            placeholders = ",".join(
                "?" for _ in contract["raws"]
            )

            raw_rows = db.execute(
                """
                SELECT *
                FROM raw_products
                WHERE id IN ({})
                ORDER BY id
                """.format(placeholders),
                contract["raws"],
            ).fetchall()

            if len(raw_rows) != len(contract["raws"]):
                raise RuntimeError(
                    "RAW count mismatch GP{}".format(source_gp)
                )

            for r in raw_rows:
                if r["global_product_id"] != source_gp:
                    raise RuntimeError(
                        "RAW{} ownership drift".format(r["id"])
                    )

                expected_variant = contract[
                    "expected_variants"
                ][r["id"]]

                if r["global_variant_id"] != expected_variant:
                    raise RuntimeError(
                        "RAW{} variant drift".format(r["id"])
                    )

            seed = raw_rows[0]

            target_gp, identity_source = create_target_gp(
                db,
                contract,
                seed,
                source_gp,
            )

            variant_map = {}

            for r in raw_rows:
                source_variant = r["global_variant_id"]

                if source_variant not in variant_map:
                    variant_map[source_variant] = clone_variant(
                        db,
                        source_variant,
                        target_gp,
                    )

                target_variant = variant_map[source_variant]

                cur = db.execute("""
                    UPDATE raw_products
                    SET global_product_id=?,
                        global_variant_id=?
                    WHERE id=?
                      AND global_product_id=?
                      AND global_variant_id=?
                """, (
                    target_gp,
                    target_variant,
                    r["id"],
                    source_gp,
                    source_variant,
                ))

                if cur.rowcount != 1:
                    raise RuntimeError(
                        "RAW{} relink rowcount={}".format(
                            r["id"],
                            cur.rowcount,
                        )
                    )

                offers = db.execute("""
                    SELECT *
                    FROM global_offers
                    WHERE raw_product_id=?
                    ORDER BY id
                """, (r["id"],)).fetchall()

                if len(offers) != 1:
                    raise RuntimeError(
                        "RAW{} offer count={}".format(
                            r["id"],
                            len(offers),
                        )
                    )

                offer = offers[0]

                cur = db.execute("""
                    UPDATE global_offers
                    SET global_product_id=?,
                        global_variant_id=?
                    WHERE id=?
                      AND raw_product_id=?
                      AND global_product_id=?
                """, (
                    target_gp,
                    target_variant,
                    offer["id"],
                    r["id"],
                    source_gp,
                ))

                if cur.rowcount != 1:
                    raise RuntimeError(
                        "O{} relink rowcount={}".format(
                            offer["id"],
                            cur.rowcount,
                        )
                    )

                cur = db.execute("""
                    UPDATE global_offer_price_history
                    SET global_product_id=?,
                        global_variant_id=?
                    WHERE global_offer_id=?
                      AND global_product_id=?
                """, (
                    target_gp,
                    target_variant,
                    offer["id"],
                    source_gp,
                ))

                # 0 history rows is valid for quarantined offers.
                if cur.rowcount < 0:
                    raise RuntimeError(
                        "history relink failure O{}".format(
                            offer["id"]
                        )
                    )

            rebuild_counter(db, source_gp)
            rebuild_counter(db, target_gp)

            created.append(
                (
                    source_gp,
                    target_gp,
                    list(contract["raws"]),
                    identity_source,
                )
            )

        # ----------------------------------------------------
        # Global post-write integrity
        # ----------------------------------------------------

        post = integrity_snapshot(db)

        blocking = {}

        # These invariants must remain absolutely clean.
        for key in (
            "active_variant_drift",
            "offer_variant_wrong_gp",
            "raw_variant_wrong_gp",
            "duplicate_active_identity_keys",
        ):
            if post[key] != 0:
                blocking[key] = post[key]

        # Existing production debt is tolerated ONLY if this
        # transaction does not make it worse.
        for key in (
            "history_wrong_gp",
            "raw_counter",
            "offer_counter",
        ):
            if post[key] > EXPECTED_BASELINE[key]:
                blocking[key + "_worsened"] = {
                    "baseline": EXPECTED_BASELINE[key],
                    "post": post[key],
                }

        if blocking:
            raise RuntimeError(
                "post integrity failure {}".format(blocking)
            )

        # ----------------------------------------------------
        # Exact contract ownership verification
        # ----------------------------------------------------

        for source_gp, target_gp, raw_ids, identity_source in created:

            target = db.execute("""
                SELECT
                    identity_source,
                    raw_product_count,
                    active_offer_count
                FROM global_products
                WHERE id=?
            """, (target_gp,)).fetchone()

            if target is None:
                raise RuntimeError(
                    "target GP{} missing".format(target_gp)
                )

            if target["identity_source"] != identity_source:
                raise RuntimeError(
                    "target GP{} identity source mismatch".format(
                        target_gp
                    )
                )

            rows = db.execute("""
                SELECT
                    id,
                    global_variant_id
                FROM raw_products
                WHERE global_product_id=?
                ORDER BY id
            """, (target_gp,)).fetchall()

            actual_ids = [x["id"] for x in rows]

            if actual_ids != sorted(raw_ids):
                raise RuntimeError(
                    "target GP{} RAW set mismatch".format(
                        target_gp
                    )
                )

            for raw in rows:
                offer = db.execute("""
                    SELECT
                        id,
                        global_product_id,
                        global_variant_id
                    FROM global_offers
                    WHERE raw_product_id=?
                """, (raw["id"],)).fetchall()

                if len(offer) != 1:
                    raise RuntimeError(
                        "RAW{} verifier offer count".format(
                            raw["id"]
                        )
                    )

                offer = offer[0]

                if offer["global_product_id"] != target_gp:
                    raise RuntimeError(
                        "RAW{} offer wrong GP".format(
                            raw["id"]
                        )
                    )

                if offer["global_variant_id"] != raw["global_variant_id"]:
                    raise RuntimeError(
                        "RAW{} offer variant mismatch".format(
                            raw["id"]
                        )
                    )

                histories = db.execute("""
                    SELECT
                        global_product_id,
                        global_variant_id
                    FROM global_offer_price_history
                    WHERE global_offer_id=?
                """, (offer["id"],)).fetchall()

                for h in histories:
                    if h["global_product_id"] != target_gp:
                        raise RuntimeError(
                            "history wrong GP O{}".format(
                                offer["id"]
                            )
                        )

                    if h["global_variant_id"] != raw["global_variant_id"]:
                        raise RuntimeError(
                            "history variant mismatch O{}".format(
                                offer["id"]
                            )
                        )

        db.commit()

        print()
        print(
            "V23.63.61 PRODUCTION REPAIR COMMIT OK"
        )
        print(
            "CREATED TARGET GPS:",
            created
        )
        print(
            "POST INTEGRITY:",
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
            "V23.63.61 PRODUCTION REPAIR ROLLBACK"
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
