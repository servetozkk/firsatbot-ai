
import sys
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

ROOT = Path.cwd()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

REAL_DB = ROOT / "data" / "products.db"

PREVIEW_DB = (
    ROOT
    / "data"
    / "_v236361_contract_repair_preview.db"
)

# ============================================================
# Approved contracts only.
# All provenance-resolved contracts included.
# ============================================================

CONTRACTS = [
    {
        "source_gp": 12,
        "raws": [348],
        "brand": "attack shark",
        "family": "x11 se",
        "model_code": "x11se",
        "ram": None,
        "storage": None,
    },
    {
        "source_gp": 29,
        "raws": [344],
        "brand": "casper",
        "family": "nirvana s100",
        "model_code": "s100.1342-bf00x-g-f",
        "ram": 16,
        "storage": 1024,
    },
    {
        "source_gp": 29,
        "raws": [345, 346],
        "brand": "casper",
        "family": "nirvana s100",
        "model_code": "s100.1362-cf00x-g-f",
        "ram": 24,
        "storage": 1024,
    },
    {
        "source_gp": 29,
        "raws": [347],
        "brand": "casper",
        "family": "nirvana s100",
        "model_code": None,
        "ram": 16,
        "storage": 500,
    },
    {
        "source_gp": 51,
        "raws": [16, 227, 228],
        "brand": "monster",
        "family": "abra a7 v15.6.4",
        "model_code": "v15.6.4",
        "ram": 16,
        "storage": 1024,
    },
    {
        "source_gp": 51,
        "raws": [226, 229],
        "brand": "monster",
        "family": "abra a5 v21.8.5",
        "model_code": "v21.8.5",
        "ram": 32,
        "storage": 1024,
    },
    {
        "source_gp": 120,
        "raws": [230],
        "brand": "lenovo",
        "family": "loq 15arp10e",
        "model_code": "83s00030trat37",
        "ram": 16,
        "storage": 512,
    },
    {
        "source_gp": 120,
        "raws": [231],
        "brand": "lenovo",
        "family": "loq",
        "model_code": "83jc000qtra29",
        "ram": 16,
        "storage": 2048,
    },
    {
        "source_gp": 134,
        "raws": [321],
        "brand": "apple",
        "family": "ipad a16",
        "model_code": "md4d4tu/a",
        "ram": 8,
        "storage": 128,
    },
    {
        "source_gp": 154,
        "raws": [258],
        "brand": "lenovo",
        "family": "ideapad slim 3",
        "model_code": None,
        "ram": 8,
        "storage": 512,
    },
    {
        "source_gp": 160,
        "raws": [304],
        "brand": "huawei",
        "family": "watch d2 + freebuds se 2 bundle",
        "model_code": None,
        "ram": None,
        "storage": None,
    },
    {
        "source_gp": 173,
        "raws": [333],
        "brand": "xaser",
        "family": "sword x60",
        "model_code": "hsr001362",
        "ram": 32,
        "storage": 1024,
    },
]


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

    cols = table_columns(
        db,
        "global_product_variants"
    )

    source = db.execute("""
        SELECT *
        FROM global_product_variants
        WHERE id=?
    """, (source_variant_id,)).fetchone()

    if source is None:
        return None

    names = [
        x
        for x in source.keys()
        if x != "id"
    ]

    values = []

    for name in names:
        if name == "global_product_id":
            values.append(target_gp)
        else:
            values.append(source[name])

    placeholders = ",".join(
        "?"
        for _ in names
    )

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

    db.execute("""
        UPDATE global_products
        SET
            raw_product_count=?,
            active_offer_count=?
        WHERE id=?
    """, (
        raw_count,
        offer_count,
        gp_id,
    ))


if PREVIEW_DB.exists():
    PREVIEW_DB.unlink()

src = sqlite3.connect(
    "file:" + str(REAL_DB).replace("\\", "/") + "?mode=ro",
    uri=True,
)

dst = sqlite3.connect(
    str(PREVIEW_DB)
)

src.backup(dst)

src.close()
dst.close()


db = sqlite3.connect(
    str(PREVIEW_DB)
)

db.row_factory = sqlite3.Row

created = []

try:

    db.execute("BEGIN IMMEDIATE")

    for contract in CONTRACTS:

        source_gp = contract["source_gp"]

        raw_rows = db.execute(
            """
            SELECT *
            FROM raw_products
            WHERE id IN ({})
            ORDER BY id
            """.format(
                ",".join(
                    "?"
                    for _ in contract["raws"]
                )
            ),
            contract["raws"],
        ).fetchall()

        if len(raw_rows) != len(contract["raws"]):
            raise RuntimeError(
                "contract RAW count mismatch source GP{}".format(
                    source_gp
                )
            )

        for r in raw_rows:
            if r["global_product_id"] != source_gp:
                raise RuntimeError(
                    "RAW{} ownership drift".format(
                        r["id"]
                    )
                )

        seed = raw_rows[0]

        # ----------------------------------------------------
        # Create target canonical.
        # Use explicit contract evidence, not parser key.
        # ----------------------------------------------------

        gp_cols = table_columns(
            db,
            "global_products"
        )

        # V23.63.61:
        # Clone the source GP row first so every existing NOT NULL /
        # provenance / timestamp column is preserved. Then override only
        # the explicit target-canonical contract fields.
        source_gp_row = db.execute("""
            SELECT *
            FROM global_products
            WHERE id=?
        """, (source_gp,)).fetchone()

        if source_gp_row is None:
            raise RuntimeError(
                "source GP{} missing during target clone".format(
                    source_gp
                )
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

        import hashlib

        identity_key = hashlib.md5(
            identity_source.encode(
                "utf-8"
            )
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

            if name in overrides:
                values.append(
                    overrides[name]
                )
            else:
                values.append(
                    source_gp_row[name]
                )

        placeholders = ",".join(
            "?"
            for _ in names
        )

        db.execute(
            "INSERT INTO global_products ({}) VALUES ({})".format(
                ",".join(names),
                placeholders,
            ),
            values,
        )

        target_gp = db.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        # ----------------------------------------------------
        # One cloned target variant per distinct source variant.
        # ----------------------------------------------------

        variant_map = {}

        for r in raw_rows:

            source_variant = r["global_variant_id"]

            if source_variant not in variant_map:
                variant_map[source_variant] = clone_variant(
                    db,
                    source_variant,
                    target_gp,
                )

            target_variant = variant_map[
                source_variant
            ]

            # ------------------------------------------------
            # raw_products
            # ------------------------------------------------

            db.execute("""
                UPDATE raw_products
                SET
                    global_product_id=?,
                    global_variant_id=?
                WHERE id=?
                  AND global_product_id=?
            """, (
                target_gp,
                target_variant,
                r["id"],
                source_gp,
            ))

            if db.total_changes < 1:
                raise RuntimeError(
                    "RAW{} relink failed".format(
                        r["id"]
                    )
                )

            # ------------------------------------------------
            # Exact offer ownership via raw_product_id
            # ------------------------------------------------

            offers = db.execute("""
                SELECT *
                FROM global_offers
                WHERE raw_product_id=?
                ORDER BY id
            """, (r["id"],)).fetchall()

            if len(offers) != 1:
                raise RuntimeError(
                    "RAW{} expected 1 offer got {}".format(
                        r["id"],
                        len(offers),
                    )
                )

            offer = offers[0]

            db.execute("""
                UPDATE global_offers
                SET
                    global_product_id=?,
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

            # ------------------------------------------------
            # Exact history via global_offer_id.
            # ------------------------------------------------

            hcols = table_columns(
                db,
                "global_offer_price_history"
            )

            if "global_offer_id" not in hcols:
                raise RuntimeError(
                    "history table lacks global_offer_id"
                )

            db.execute("""
                UPDATE global_offer_price_history
                SET
                    global_product_id=?,
                    global_variant_id=?
                WHERE global_offer_id=?
                  AND global_product_id=?
            """, (
                target_gp,
                target_variant,
                offer["id"],
                source_gp,
            ))

        rebuild_counter(
            db,
            source_gp
        )

        rebuild_counter(
            db,
            target_gp
        )

        created.append(
            (
                source_gp,
                target_gp,
                contract["raws"],
                identity_source,
            )
        )

    # ========================================================
    # Integrity gates
    #
    # V23.63.61 baseline-aware policy:
    #
    # Existing DB baseline before this preview:
    #   active variant drift = 0
    #   wide/inactive drift   = 24
    #   raw counter mismatch  = 13
    #   offer counter mismatch= 5
    #
    # Repair must introduce NO new referential corruption and
    # must never worsen existing counter debt.
    # ========================================================

    BASELINE_RAW_COUNTER = 13
    BASELINE_OFFER_COUNTER = 5
    BASELINE_WIDE_VARIANT_DRIFT = 24

    checks = {}

    checks["history_wrong_gp"] = db.execute("""
        SELECT COUNT(*)
        FROM global_offer_price_history h
        JOIN global_product_variants gv
          ON gv.id=h.global_variant_id
        WHERE h.global_variant_id IS NOT NULL
          AND h.global_product_id != gv.global_product_id
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

    checks["active_variant_drift"] = db.execute("""
        SELECT COUNT(*)
        FROM global_offers go
        JOIN raw_products rp
          ON rp.id=go.raw_product_id
        WHERE go.is_active=1
          AND go.global_variant_id IS NOT NULL
          AND rp.global_variant_id IS NOT NULL
          AND go.global_variant_id != rp.global_variant_id
    """).fetchone()[0]

    checks["wide_variant_drift"] = db.execute("""
        SELECT COUNT(*)
        FROM global_offers go
        JOIN raw_products rp
          ON rp.id=go.raw_product_id
        WHERE go.global_variant_id IS NOT NULL
          AND rp.global_variant_id IS NOT NULL
          AND go.global_variant_id != rp.global_variant_id
    """).fetchone()[0]

    checks["raw_counter"] = db.execute("""
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.raw_product_count != (
            SELECT COUNT(*)
            FROM raw_products rp
            WHERE rp.global_product_id=gp.id
        )
    """).fetchone()[0]

    checks["offer_counter"] = db.execute("""
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

    checks["duplicate_identity_keys"] = db.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT identity_key,COUNT(*) c
            FROM global_products
            WHERE identity_key IS NOT NULL
            GROUP BY identity_key
            HAVING COUNT(*)>1
        )
    """).fetchone()[0]

    blocking = {}

    # Referential invariants must stay absolutely clean.
    for name in (
        "history_wrong_gp",
        "offer_variant_wrong_gp",
        "raw_variant_wrong_gp",
        "active_variant_drift",
        "duplicate_identity_keys",
    ):
        if checks[name] != 0:
            blocking[name] = checks[name]

    # Existing historical/inactive debt may remain, but repair
    # is forbidden from making it worse.
    if checks["wide_variant_drift"] > BASELINE_WIDE_VARIANT_DRIFT:
        blocking["wide_variant_drift_worsened"] = (
            checks["wide_variant_drift"],
            BASELINE_WIDE_VARIANT_DRIFT,
        )

    if checks["raw_counter"] > BASELINE_RAW_COUNTER:
        blocking["raw_counter_worsened"] = (
            checks["raw_counter"],
            BASELINE_RAW_COUNTER,
        )

    if checks["offer_counter"] > BASELINE_OFFER_COUNTER:
        blocking["offer_counter_worsened"] = (
            checks["offer_counter"],
            BASELINE_OFFER_COUNTER,
        )

    print(
        "BASELINE:",
        {
            "wide_variant_drift": BASELINE_WIDE_VARIANT_DRIFT,
            "active_variant_drift": 0,
            "raw_counter": BASELINE_RAW_COUNTER,
            "offer_counter": BASELINE_OFFER_COUNTER,
        }
    )

    print(
        "POST REPAIR:",
        checks
    )

    if blocking:
        raise RuntimeError(
            "integrity gate failed {}".format(
                blocking
            )
        )

    # ========================================================
    # V23.63.61 POST-REPAIR CONTRACT VERIFIER
    #
    # Runs BEFORE commit.
    # Any ownership/contract mismatch raises and causes rollback.
    # ========================================================

    verifier_errors = []

    # Resolve created target GP by explicit source/raw contract.
    created_map = {
        (
            source_gp,
            tuple(raw_ids),
        ): target_gp
        for (
            source_gp,
            target_gp,
            raw_ids,
            _identity_source,
        ) in created
    }

    print()
    print("=" * 120)
    print("POST-REPAIR CONTRACT VERIFIER")
    print("=" * 120)

    verified_targets = 0
    verified_raws = 0
    verified_offers = 0
    verified_history = 0

    for contract in CONTRACTS:

        source_gp = contract["source_gp"]
        raw_ids = tuple(
            contract["raws"]
        )

        target_gp = created_map.get(
            (
                source_gp,
                raw_ids,
            )
        )

        if target_gp is None:
            verifier_errors.append(
                "missing created target for source GP{} raws={}".format(
                    source_gp,
                    raw_ids,
                )
            )
            continue

        target = db.execute("""
            SELECT
                id,
                canonical_name,
                normalized_brand,
                family,
                ram_gb,
                storage_gb,
                model_code,
                identity_source,
                identity_key,
                status,
                raw_product_count,
                active_offer_count
            FROM global_products
            WHERE id=?
        """, (target_gp,)).fetchone()

        if target is None:
            verifier_errors.append(
                "target GP{} missing".format(
                    target_gp
                )
            )
            continue

        verified_targets += 1

        expected_source = (
            "identity_v236361_contract:"
            "brand={}|family={}|ram={}|storage={}|model_code={}"
        ).format(
            contract["brand"] or "",
            contract["family"] or "",
            contract["ram"]
            if contract["ram"] is not None
            else "",
            contract["storage"]
            if contract["storage"] is not None
            else "",
            contract["model_code"] or "",
        )

        # ----------------------------------------------------
        # Target canonical contract
        # ----------------------------------------------------

        expected_fields = {
            "normalized_brand": contract["brand"],
            "family": contract["family"],
            "ram_gb": contract["ram"],
            "storage_gb": contract["storage"],
            "model_code": contract["model_code"],
            "identity_source": expected_source,
            "status": "ACTIVE",
        }

        for field, expected in expected_fields.items():

            actual = target[field]

            if actual != expected:
                verifier_errors.append(
                    "GP{} {} mismatch expected={!r} actual={!r}".format(
                        target_gp,
                        field,
                        expected,
                        actual,
                    )
                )

        # ----------------------------------------------------
        # Exact target raw ownership
        # ----------------------------------------------------

        target_raw_rows = db.execute("""
            SELECT
                id,
                global_product_id,
                global_variant_id
            FROM raw_products
            WHERE global_product_id=?
            ORDER BY id
        """, (target_gp,)).fetchall()

        actual_target_raw_ids = [
            r["id"]
            for r in target_raw_rows
        ]

        if actual_target_raw_ids != sorted(
            contract["raws"]
        ):
            verifier_errors.append(
                "GP{} target RAW set mismatch expected={} actual={}".format(
                    target_gp,
                    sorted(contract["raws"]),
                    actual_target_raw_ids,
                )
            )

        # Counter must exactly describe target ownership.
        if target["raw_product_count"] != len(
            target_raw_rows
        ):
            verifier_errors.append(
                "GP{} raw counter mismatch stored={} actual={}".format(
                    target_gp,
                    target["raw_product_count"],
                    len(target_raw_rows),
                )
            )

        for raw in target_raw_rows:

            verified_raws += 1

            raw_id = raw["id"]
            target_variant = raw[
                "global_variant_id"
            ]

            # Variant must belong to the target canonical.
            if target_variant is not None:

                variant = db.execute("""
                    SELECT
                        id,
                        global_product_id
                    FROM global_product_variants
                    WHERE id=?
                """, (target_variant,)).fetchone()

                if variant is None:
                    verifier_errors.append(
                        "RAW{} target variant {} missing".format(
                            raw_id,
                            target_variant,
                        )
                    )

                elif variant[
                    "global_product_id"
                ] != target_gp:
                    verifier_errors.append(
                        "RAW{} variant {} belongs GP{} not GP{}".format(
                            raw_id,
                            target_variant,
                            variant["global_product_id"],
                            target_gp,
                        )
                    )

            # ------------------------------------------------
            # Exact offer ownership
            # ------------------------------------------------

            offers = db.execute("""
                SELECT
                    id,
                    raw_product_id,
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
                verifier_errors.append(
                    "RAW{} expected exactly 1 offer got {}".format(
                        raw_id,
                        len(offers),
                    )
                )
                continue

            offer = offers[0]

            verified_offers += 1

            if offer[
                "global_product_id"
            ] != target_gp:
                verifier_errors.append(
                    "O{} RAW{} wrong GP expected={} actual={}".format(
                        offer["id"],
                        raw_id,
                        target_gp,
                        offer["global_product_id"],
                    )
                )

            if offer[
                "global_variant_id"
            ] != target_variant:
                verifier_errors.append(
                    "O{} RAW{} variant mismatch raw={} offer={}".format(
                        offer["id"],
                        raw_id,
                        target_variant,
                        offer["global_variant_id"],
                    )
                )

            # ------------------------------------------------
            # Exact history ownership through global_offer_id
            # ------------------------------------------------

            histories = db.execute("""
                SELECT
                    id,
                    global_offer_id,
                    global_product_id,
                    global_variant_id
                FROM global_offer_price_history
                WHERE global_offer_id=?
                ORDER BY id
            """, (offer["id"],)).fetchall()

            for history in histories:

                verified_history += 1

                if history[
                    "global_product_id"
                ] != target_gp:
                    verifier_errors.append(
                        "H{} O{} wrong GP expected={} actual={}".format(
                            history["id"],
                            offer["id"],
                            target_gp,
                            history["global_product_id"],
                        )
                    )

                if history[
                    "global_variant_id"
                ] != target_variant:
                    verifier_errors.append(
                        "H{} O{} variant mismatch expected={} actual={}".format(
                            history["id"],
                            offer["id"],
                            target_variant,
                            history["global_variant_id"],
                        )
                    )

        # ----------------------------------------------------
        # Target active-offer counter
        # ----------------------------------------------------

        actual_active_offer_count = db.execute("""
            SELECT COUNT(*)
            FROM global_offers
            WHERE global_product_id=?
              AND is_active=1
              AND is_hidden=0
              AND lifecycle_status='ACTIVE'
              AND current_price>0
        """, (target_gp,)).fetchone()[0]

        if (
            target["active_offer_count"]
            != actual_active_offer_count
        ):
            verifier_errors.append(
                "GP{} offer counter mismatch stored={} actual={}".format(
                    target_gp,
                    target["active_offer_count"],
                    actual_active_offer_count,
                )
            )

        # ----------------------------------------------------
        # No moved RAW may remain on source GP.
        # ----------------------------------------------------

        source_residue = db.execute(
            """
            SELECT COUNT(*)
            FROM raw_products
            WHERE global_product_id=?
              AND id IN ({})
            """.format(
                ",".join(
                    "?"
                    for _ in contract["raws"]
                )
            ),
            (
                source_gp,
                *contract["raws"],
            ),
        ).fetchone()[0]

        if source_residue != 0:
            verifier_errors.append(
                "source GP{} still owns {} moved RAW(s) from {}".format(
                    source_gp,
                    source_residue,
                    contract["raws"],
                )
            )

        print(
            "GP{} -> GP{} RAW={} RAW_COUNT={} ACTIVE_OFFERS={}".format(
                source_gp,
                target_gp,
                contract["raws"],
                target["raw_product_count"],
                target["active_offer_count"],
            )
        )

    # ========================================================
    # Blocked contracts MUST remain untouched.
    # ========================================================

    blocked_expectations = {}

    for raw_id, expected_gp in blocked_expectations.items():

        row = db.execute("""
            SELECT
                global_product_id
            FROM raw_products
            WHERE id=?
        """, (raw_id,)).fetchone()

        if row is None:
            verifier_errors.append(
                "blocked RAW{} missing".format(
                    raw_id
                )
            )

        elif row[
            "global_product_id"
        ] != expected_gp:
            verifier_errors.append(
                "blocked RAW{} moved unexpectedly GP{} -> GP{}".format(
                    raw_id,
                    expected_gp,
                    row["global_product_id"],
                )
            )

    # ========================================================
    # Source GP counter verification for every touched source.
    # ========================================================

    touched_sources = sorted({
        c["source_gp"]
        for c in CONTRACTS
    })

    for source_gp in touched_sources:

        gp = db.execute("""
            SELECT
                raw_product_count,
                active_offer_count
            FROM global_products
            WHERE id=?
        """, (source_gp,)).fetchone()

        if gp is None:
            verifier_errors.append(
                "source GP{} missing after repair".format(
                    source_gp
                )
            )
            continue

        actual_raw = db.execute("""
            SELECT COUNT(*)
            FROM raw_products
            WHERE global_product_id=?
        """, (source_gp,)).fetchone()[0]

        actual_offer = db.execute("""
            SELECT COUNT(*)
            FROM global_offers
            WHERE global_product_id=?
              AND is_active=1
              AND is_hidden=0
              AND lifecycle_status='ACTIVE'
              AND current_price>0
        """, (source_gp,)).fetchone()[0]

        if gp[
            "raw_product_count"
        ] != actual_raw:
            verifier_errors.append(
                "source GP{} raw counter stored={} actual={}".format(
                    source_gp,
                    gp["raw_product_count"],
                    actual_raw,
                )
            )

        if gp[
            "active_offer_count"
        ] != actual_offer:
            verifier_errors.append(
                "source GP{} offer counter stored={} actual={}".format(
                    source_gp,
                    gp["active_offer_count"],
                    actual_offer,
                )
            )

    print()
    print(
        "VERIFIED TARGETS:",
        verified_targets
    )

    print(
        "VERIFIED RAWS:",
        verified_raws
    )

    print(
        "VERIFIED OFFERS:",
        verified_offers
    )

    print(
        "VERIFIED HISTORY:",
        verified_history
    )

    print(
        "VERIFIER ERRORS:",
        len(verifier_errors)
    )

    if verifier_errors:

        for error in verifier_errors:
            print(
                "VERIFY FAIL:",
                error
            )

        raise RuntimeError(
            "post-repair contract verifier failed: {}".format(
                len(verifier_errors)
            )
        )

    print(
        "POST-REPAIR CONTRACT VERIFIER PASS"
    )

    # Commit only after both global integrity and contract
    # ownership verification have passed.
    db.commit()

    print(
        "V23.63.61 COPY-DB TRANSACTION PREVIEW OK"
    )

    print(
        "CREATED TARGET GPS:",
        created
    )

    print(
        "INTEGRITY:",
        checks
    )

finally:
    db.close()


# ------------------------------------------------------------
# Verify real DB unchanged by checking split RAW ownership.
# ------------------------------------------------------------

real = sqlite3.connect(
    "file:" + str(REAL_DB).replace("\\", "/") + "?mode=ro",
    uri=True,
)

preview = sqlite3.connect(
    str(PREVIEW_DB)
)

print()
print("OWNERSHIP COMPARISON")

for contract in CONTRACTS:

    for raw_id in contract["raws"]:

        before = real.execute("""
            SELECT
                global_product_id,
                global_variant_id
            FROM raw_products
            WHERE id=?
        """, (raw_id,)).fetchone()

        after = preview.execute("""
            SELECT
                global_product_id,
                global_variant_id
            FROM raw_products
            WHERE id=?
        """, (raw_id,)).fetchone()

        print(
            "RAW{} real={} preview={}".format(
                raw_id,
                before,
                after,
            )
        )

real.close()
preview.close()

print()
print(
    "REAL DATABASE UNCHANGED"
)
