
import sqlite3
from pathlib import Path
from collections import defaultdict

ROOT = Path.cwd()
DB = ROOT / "data" / "products.db"

OUT = (
    Path.home()
    / "Downloads"
    / "v236361-repair-planner-dry-run.txt"
)

# ============================================================
# Explicit repair plan scope.
#
# KEEP means remain on current GP.
# SPLIT means must leave current GP and get separate ownership.
#
# No DB mutations occur in this script.
# ============================================================

PLAN = {

    # Attack Shark X11:
    # current GP12 canonical = X11 Superlight
    12: {
        13:  "KEEP",
        348: "SPLIT",
    },

    # Casper Nirvana S100:
    # RAW30 remains baseline GP29.
    # Different SKU/configurations split.
    29: {
        30:  "KEEP",
        344: "SPLIT",
        345: "SPLIT",
        346: "SPLIT",
        347: "SPLIT",
    },

    # GP51 canonical Tulpar is itself inconsistent with all
    # currently attached raw members.
    #
    # All attached Abra products should leave GP51.
    51: {
        16:  "SPLIT",
        226: "SPLIT",
        227: "SPLIT",
        228: "SPLIT",
        229: "SPLIT",
    },

    # Lenovo LOQ:
    # 83S0002VTR baseline stays together.
    120: {
        145: "KEEP",
        230: "SPLIT",
        231: "SPLIT",
        232: "KEEP",
    },

    # Lenovo IdeaPad Slim 3:
    # i3 / 82X700G1TX baseline stays.
    154: {
        18:  "KEEP",
        258: "SPLIT",
        259: "KEEP",
    },

    # Sword X55 / X60
    173: {
        29:  "KEEP",
        332: "KEEP",
        333: "SPLIT",
        334: "KEEP",
    },

    # GP134:
    # iPad is the only known bad member.
    134: {
        321: "SPLIT",
    },

    # GP160:
    # Watch D2 + FreeBuds bundle is the only confirmed bad member.
    160: {
        304: "SPLIT",
    },
}


db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True,
)

db.row_factory = sqlite3.Row


def table_exists(name):
    return db.execute("""
        SELECT 1
        FROM sqlite_master
        WHERE type='table'
          AND name=?
    """, (name,)).fetchone() is not None


def columns(table):
    return {
        r["name"]
        for r in db.execute(
            "PRAGMA table_info({})".format(table)
        )
    }


def fetch_raw(raw_id):

    return db.execute("""
        SELECT
            id,
            store_code,
            store_product_id,
            title_raw,
            identity_key,
            global_product_id,
            global_variant_id,
            reconciliation_status
        FROM raw_products
        WHERE id=?
    """, (raw_id,)).fetchone()


def fetch_offers(raw_id):

    if not table_exists("global_offers"):
        return []

    return db.execute("""
        SELECT *
        FROM global_offers
        WHERE raw_product_id=?
        ORDER BY id
    """, (raw_id,)).fetchall()


def fetch_history_for_offer(offer):

    if not table_exists(
        "global_offer_price_history"
    ):
        return []

    cols = columns(
        "global_offer_price_history"
    )

    # Prefer exact offer linkage if schema has global_offer_id.
    if "global_offer_id" in cols:
        return db.execute("""
            SELECT *
            FROM global_offer_price_history
            WHERE global_offer_id=?
            ORDER BY id
        """, (offer["id"],)).fetchall()

    # Otherwise fail closed to matching ownership evidence.
    clauses = []
    params = []

    if (
        "global_product_id" in cols
        and "global_product_id" in offer.keys()
    ):
        clauses.append(
            "global_product_id=?"
        )
        params.append(
            offer["global_product_id"]
        )

    if (
        "global_variant_id" in cols
        and "global_variant_id" in offer.keys()
        and offer["global_variant_id"] is not None
    ):
        clauses.append(
            "global_variant_id=?"
        )
        params.append(
            offer["global_variant_id"]
        )

    # Do not pretend ambiguous history is safe.
    if not clauses:
        return []

    sql = (
        "SELECT * FROM global_offer_price_history "
        "WHERE "
        + " AND ".join(clauses)
        + " ORDER BY id"
    )

    return db.execute(
        sql,
        params
    ).fetchall()


def raw_variant_peer_count(
    gp_id,
    variant_id,
):

    if variant_id is None:
        return 0

    return db.execute("""
        SELECT COUNT(*)
        FROM raw_products
        WHERE global_product_id=?
          AND global_variant_id=?
    """, (
        gp_id,
        variant_id,
    )).fetchone()[0]


def offer_variant_peer_count(
    gp_id,
    variant_id,
):

    if (
        variant_id is None
        or not table_exists("global_offers")
    ):
        return 0

    return db.execute("""
        SELECT COUNT(*)
        FROM global_offers
        WHERE global_product_id=?
          AND global_variant_id=?
    """, (
        gp_id,
        variant_id,
    )).fetchone()[0]


def external_raw_refs(raw_id):

    refs = []

    for table in (
        "product_match_reviews",
    ):
        if not table_exists(table):
            continue

        cols = columns(table)

        if "raw_product_id" not in cols:
            continue

        count = db.execute(
            "SELECT COUNT(*) FROM {} "
            "WHERE raw_product_id=?".format(
                table
            ),
            (raw_id,),
        ).fetchone()[0]

        if count:
            refs.append(
                (table, count)
            )

    return refs


def external_gp_variant_refs(
    gp_id,
    variant_id,
):

    refs = []

    for table in (
        "advanced_alerts",
        "bulk_identity_links",
        "global_price_alerts",
    ):

        if not table_exists(table):
            continue

        cols = columns(table)

        conditions = []
        params = []

        if "global_product_id" in cols:
            conditions.append(
                "global_product_id=?"
            )
            params.append(gp_id)

        if (
            "global_variant_id" in cols
            and variant_id is not None
        ):
            conditions.append(
                "global_variant_id=?"
            )
            params.append(
                variant_id
            )

        if not conditions:
            continue

        sql = (
            "SELECT COUNT(*) FROM {} WHERE ".format(
                table
            )
            + " OR ".join(
                "({})".format(x)
                for x in conditions
            )
        )

        count = db.execute(
            sql,
            params
        ).fetchone()[0]

        if count:
            refs.append(
                (table, count)
            )

    return refs


rows_out = []


for gp_id, raw_plan in PLAN.items():

    gp = db.execute("""
        SELECT
            id,
            canonical_name,
            identity_key,
            identity_source,
            status,
            raw_product_count,
            active_offer_count
        FROM global_products
        WHERE id=?
    """, (gp_id,)).fetchone()

    if gp is None:
        rows_out.append({
            "gp": gp_id,
            "fatal": "GLOBAL PRODUCT MISSING",
        })
        continue

    current_raws = db.execute("""
        SELECT id
        FROM raw_products
        WHERE global_product_id=?
        ORDER BY id
    """, (gp_id,)).fetchall()

    current_raw_ids = {
        r["id"]
        for r in current_raws
    }

    planned_ids = set(
        raw_plan.keys()
    )

    # If plan enumerates the whole GP, exact equality is expected.
    # For single-bad-member GPs (134,160) plan intentionally only
    # contains the bad raw.
    full_scope = gp_id not in (
        134,
        160,
    )

    gp_precheck_errors = []

    if (
        full_scope
        and current_raw_ids != planned_ids
    ):
        gp_precheck_errors.append(
            "PLAN/CURRENT RAW SET MISMATCH "
            "current={} planned={}".format(
                sorted(current_raw_ids),
                sorted(planned_ids),
            )
        )

    for raw_id, action in raw_plan.items():

        r = fetch_raw(raw_id)

        result = {
            "gp": gp_id,
            "raw_id": raw_id,
            "action": action,
            "safe": True,
            "reasons": [],
        }

        if r is None:
            result["safe"] = False
            result["reasons"].append(
                "RAW missing"
            )
            rows_out.append(result)
            continue

        result.update({
            "store": r["store_code"],
            "title": r["title_raw"],
            "variant_id": r["global_variant_id"],
            "reconciliation": r["reconciliation_status"],
            "current_gp": r["global_product_id"],
        })

        if r["global_product_id"] != gp_id:
            result["safe"] = False
            result["reasons"].append(
                "RAW current GP mismatch"
            )

        if action == "KEEP":
            rows_out.append(result)
            continue

        if action != "SPLIT":
            result["safe"] = False
            result["reasons"].append(
                "unknown action"
            )
            rows_out.append(result)
            continue

        offers = fetch_offers(raw_id)

        result["offer_ids"] = [
            x["id"]
            for x in offers
        ]

        # Every split raw should normally have one offer in this DB.
        if len(offers) != 1:
            result["safe"] = False
            result["reasons"].append(
                "expected exactly 1 offer, got {}".format(
                    len(offers)
                )
            )

        history_ids = []

        ambiguous_history = False

        for offer in offers:

            histories = fetch_history_for_offer(
                offer
            )

            history_ids.extend(
                x["id"]
                for x in histories
            )

            # If history lacks direct global_offer_id,
            # a shared variant can produce ambiguous rows.
            hcols = columns(
                "global_offer_price_history"
            )

            if (
                "global_offer_id" not in hcols
                and r["global_variant_id"] is not None
            ):
                raw_peer_count = raw_variant_peer_count(
                    gp_id,
                    r["global_variant_id"],
                )

                if raw_peer_count > 1:
                    ambiguous_history = True

        result["history_ids"] = sorted(
            set(history_ids)
        )

        if ambiguous_history:
            result["safe"] = False
            result["reasons"].append(
                "history ownership ambiguous because "
                "variant is shared and history has no direct offer linkage"
            )

        variant_id = r["global_variant_id"]

        result["variant_raw_peers"] = (
            raw_variant_peer_count(
                gp_id,
                variant_id,
            )
        )

        result["variant_offer_peers"] = (
            offer_variant_peer_count(
                gp_id,
                variant_id,
            )
        )

        # A shared variant MUST NOT be moved wholesale.
        if (
            variant_id is not None
            and (
                result["variant_raw_peers"] > 1
                or result["variant_offer_peers"] > 1
            )
        ):
            result["reasons"].append(
                "shared variant: repair must clone/create "
                "target variant; never move source variant wholesale"
            )

        raw_refs = external_raw_refs(
            raw_id
        )

        gp_refs = external_gp_variant_refs(
            gp_id,
            variant_id,
        )

        result["external_raw_refs"] = raw_refs
        result["external_gp_variant_refs"] = gp_refs

        if raw_refs:
            result["safe"] = False
            result["reasons"].append(
                "external raw references present"
            )

        # GP-level external references do not automatically make
        # the raw unsafe, but they prohibit deleting/repurposing
        # the source GP during split.
        if gp_refs:
            result["reasons"].append(
                "source GP/variant has external references; "
                "source canonical must be preserved"
            )

        rows_out.append(result)


# ============================================================
# Output
# ============================================================

with OUT.open(
    "w",
    encoding="utf-8",
    newline="\n",
) as f:

    def out(*args):
        print(*args, file=f)

    out("=" * 155)
    out("V23.63.61 TRANSACTION REPAIR PLANNER / DRY RUN")
    out("READ ONLY - NO DATABASE WRITES")
    out("=" * 155)

    out()
    out(
        "TARGET GPS:",
        tuple(PLAN.keys())
    )

    out()

    safe_splits = 0
    blocked_splits = 0

    for gp_id in PLAN:

        gp = db.execute("""
            SELECT
                canonical_name,
                identity_source
            FROM global_products
            WHERE id=?
        """, (gp_id,)).fetchone()

        out()
        out("#" * 155)
        out(
            "GP{}".format(
                gp_id
            )
        )
        out("#" * 155)

        if gp:
            out(
                "CANONICAL:",
                gp["canonical_name"]
            )
            out(
                "IDENTITY SOURCE:",
                gp["identity_source"]
            )

        gp_rows = [
            x
            for x in rows_out
            if x.get("gp") == gp_id
            and "raw_id" in x
        ]

        for x in gp_rows:

            out()
            out("-" * 155)

            out(
                "RAW{} => {}".format(
                    x["raw_id"],
                    x["action"]
                )
            )

            out(
                "STORE:",
                x.get("store")
            )

            out(
                "STATUS:",
                x.get("reconciliation")
            )

            out(
                "VARIANT:",
                x.get("variant_id")
            )

            out(
                "TITLE:",
                x.get("title")
            )

            if x["action"] == "SPLIT":

                out(
                    "OFFER IDS:",
                    x.get(
                        "offer_ids",
                        []
                    )
                )

                out(
                    "HISTORY IDS:",
                    x.get(
                        "history_ids",
                        []
                    )
                )

                out(
                    "VARIANT RAW PEERS:",
                    x.get(
                        "variant_raw_peers"
                    )
                )

                out(
                    "VARIANT OFFER PEERS:",
                    x.get(
                        "variant_offer_peers"
                    )
                )

                out(
                    "EXTERNAL RAW REFS:",
                    x.get(
                        "external_raw_refs",
                        []
                    )
                )

                out(
                    "EXTERNAL GP/VARIANT REFS:",
                    x.get(
                        "external_gp_variant_refs",
                        []
                    )
                )

                if x["safe"]:
                    safe_splits += 1
                    out(
                        "SAFE_TO_REPAIR: YES"
                    )
                else:
                    blocked_splits += 1
                    out(
                        "SAFE_TO_REPAIR: NO"
                    )

                out(
                    "REASONS:"
                )

                if x["reasons"]:
                    for reason in x["reasons"]:
                        out(
                            " -",
                            reason
                        )
                else:
                    out(
                        " - exact raw/offer/history ownership"
                    )

            else:
                out(
                    "SAFE_TO_REPAIR: PRESERVE"
                )

    out()
    out("=" * 155)
    out("SUMMARY")
    out("=" * 155)

    out(
        "SAFE SPLIT RAWS:",
        safe_splits
    )

    out(
        "BLOCKED SPLIT RAWS:",
        blocked_splits
    )

    out()
    out(
        "DATABASE UNCHANGED"
    )

    out("=" * 155)


db.close()

print(
    "REPAIR PLANNER TAMAMLANDI"
)

print(
    "FILE:",
    OUT
)

safe_splits = sum(
    1
    for x in rows_out
    if x.get("action") == "SPLIT"
    and x.get("safe") is True
)

blocked_splits = sum(
    1
    for x in rows_out
    if x.get("action") == "SPLIT"
    and x.get("safe") is False
)

print(
    "SAFE SPLIT RAWS:",
    safe_splits
)

print(
    "BLOCKED SPLIT RAWS:",
    blocked_splits
)

print(
    "DATABASE UNCHANGED"
)
