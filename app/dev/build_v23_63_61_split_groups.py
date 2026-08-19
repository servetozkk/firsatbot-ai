
import sys
import json
import re
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict

ROOT = Path.cwd()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

DB = ROOT / "data" / "products.db"

OUT = (
    Path.home()
    / "Downloads"
    / "v236361-split-group-builder.txt"
)

# ============================================================
# Explicit split scope from approved repair planner.
# ============================================================

SPLIT_RAWS = {
    12:  [348],

    29:  [344,345,346,347],

    51:  [16,226,227,228,229],

    120: [230,231],

    154: [258],

    173: [333],

    134: [321],

    160: [304],
}


# ============================================================
# Explicit high-confidence grouping locks.
#
# These are not DB writes.
# They only declare which split RAWs are already proven
# equivalent enough to share one future canonical.
# ============================================================

LOCKED_GROUPS = {

    12: {
        "x11-se": [348],
    },

    29: {
        "s100-1342-bf00x": [344],
        "s100-1362-cf00x": [345,346],
        "s100-1362-500gb-unknown-sku": [347],
    },

    51: {
        # RAW16 / RAW227 / RAW228 are provenance-confirmed
        # Monster Abra A7 V15.6.4 records.
        # RAW228 Teknosa evidence explicitly contains:
        # model=Abra A7 V15.6.4, RAM=16GB, SSD=1024GB.
        "abra-a7-v15.6.4": [16,227,228],

        "abra-a5-v21.8.5": [226,229],
    },

    120: {
        "loq-83s00030trat37": [230],
        "loq-83jc000qtra29": [231],
    },

    154: {
        "ideapad-slim3-i5-13420h": [258],
    },

    173: {
        "sword-x60": [333],
    },

    134: {
        "ipad-a16-md4d4tu-a": [321],
    },

    160: {
        "watch-d2-freebuds-bundle": [304],
    },
}


MANUAL_GROUPS = set()


def load_specs(value):
    if not value:
        return {}

    try:
        obj = json.loads(value)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def norm(value):
    return re.sub(
        r"\s+",
        " ",
        S._ascii_fold(value or "").lower()
    ).strip()


def fetch_raw(db, raw_id):

    return db.execute("""
        SELECT
            id,
            store_code,
            store_product_id,
            title_raw,
            brand_raw,
            model_raw,
            description_raw,
            specifications_raw,
            category_raw,
            global_product_id,
            global_variant_id,
            reconciliation_status
        FROM raw_products
        WHERE id=?
    """, (raw_id,)).fetchone()


db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True
)

db.row_factory = sqlite3.Row


results = []


for gp_id, groups in LOCKED_GROUPS.items():

    planned = set(
        SPLIT_RAWS.get(gp_id, [])
    )

    grouped = set()

    for group_name, raw_ids in groups.items():
        grouped.update(raw_ids)

    if grouped != planned:
        raise RuntimeError(
            "GP{} split/group coverage mismatch planned={} grouped={}".format(
                gp_id,
                sorted(planned),
                sorted(grouped),
            )
        )

    for group_name, raw_ids in groups.items():

        group_items = []

        for raw_id in raw_ids:

            r = fetch_raw(
                db,
                raw_id
            )

            if r is None:
                raise RuntimeError(
                    "RAW{} missing".format(
                        raw_id
                    )
                )

            if r["global_product_id"] != gp_id:
                raise RuntimeError(
                    "RAW{} ownership drift expected GP{} got GP{}".format(
                        raw_id,
                        gp_id,
                        r["global_product_id"],
                    )
                )

            product = SimpleNamespace(
                name=r["title_raw"] or "",
                brand=r["brand_raw"] or "",
                model=r["model_raw"] or "",
                description=r["description_raw"] or "",
                specifications=load_specs(
                    r["specifications_raw"]
                ),
                category=r["category_raw"] or "",
                product_code=r["store_product_id"] or "",
            )

            parsed = S.parse(product)
            explained = S.explain(product)

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

            histories = []

            for offer in offers:

                h = db.execute("""
                    SELECT
                        id,
                        global_product_id,
                        global_variant_id
                    FROM global_offer_price_history
                    WHERE global_offer_id=?
                    ORDER BY id
                """, (offer["id"],)).fetchall()

                histories.extend(h)

            group_items.append({
                "raw_id": raw_id,
                "store": r["store_code"],
                "status": r["reconciliation_status"],
                "source_gp": gp_id,
                "source_variant": r["global_variant_id"],
                "title": r["title_raw"],

                "brand": parsed.brand,
                "family": parsed.family,
                "variant": parsed.variant,
                "ram": parsed.ram_gb,
                "storage": parsed.storage_gb,
                "network": parsed.network,
                "model_code": parsed.model_code,

                "identity_source": explained.get(
                    "identity_source"
                ),

                "identity_key": explained.get(
                    "identity_key"
                ),

                "offer_ids": [
                    x["id"]
                    for x in offers
                ],

                "history_ids": [
                    x["id"]
                    for x in histories
                ],
            })

        # ----------------------------------------------------
        # Group evidence gate
        # ----------------------------------------------------

        identity_sources = {
            x["identity_source"]
            for x in group_items
            if x["identity_source"]
        }

        identity_keys = {
            x["identity_key"]
            for x in group_items
            if x["identity_key"]
        }

        brands = {
            x["brand"]
            for x in group_items
            if x["brand"]
        }

        safe = True
        reasons = []

        manual = (
            gp_id,
            group_name,
        ) in MANUAL_GROUPS

        if manual:
            safe = False
            reasons.append(
                "manual evidence lock: source title insufficient for automatic canonical grouping"
            )

        if len(brands) > 1:
            safe = False
            reasons.append(
                "multiple brands inside target group"
            )

        # Multiple parser identities do not automatically fail:
        # parser family strings can differ across stores.
        # But report it explicitly.
        if len(identity_sources) > 1:
            reasons.append(
                "multiple parser identity sources inside group"
            )

        if len(identity_keys) > 1:
            reasons.append(
                "multiple parser identity keys inside group"
            )

        # Canonical seed:
        # choose strongest/most complete record deterministically.
        seed = sorted(
            group_items,
            key=lambda x: (
                0 if x["model_code"] else 1,
                0 if x["storage"] is not None else 1,
                0 if x["ram"] is not None else 1,
                -len(norm(x["title"])),
                x["raw_id"],
            )
        )[0]

        results.append({
            "source_gp": gp_id,
            "group_name": group_name,
            "safe": safe,
            "manual": manual,
            "reasons": reasons,

            "seed_raw": seed["raw_id"],
            "seed_identity_source": seed["identity_source"],
            "seed_identity_key": seed["identity_key"],

            "items": group_items,
        })


# ============================================================
# Cross-group collision guard.
# Within the same source GP, two target groups must not resolve
# to identical parser identity keys unless deliberately manual.
# ============================================================

by_gp = defaultdict(list)

for result in results:
    by_gp[
        result["source_gp"]
    ].append(result)


for gp_id, gp_results in by_gp.items():

    key_map = defaultdict(list)

    for result in gp_results:

        if result["manual"]:
            continue

        key = result["seed_identity_key"]

        if key:
            key_map[key].append(
                result
            )

    for key, collision_groups in key_map.items():

        if len(collision_groups) <= 1:
            continue

        names = [
            x["group_name"]
            for x in collision_groups
        ]

        for result in collision_groups:
            result["safe"] = False
            result["reasons"].append(
                "cross-group parser identity collision with groups={}".format(
                    names
                )
            )


# ============================================================
# Output
# ============================================================

with OUT.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as f:

    def out(*args):
        print(*args, file=f)

    out("=" * 155)
    out("V23.63.61 SPLIT GROUP BUILDER")
    out("READ ONLY - NO DATABASE WRITES")
    out("=" * 155)

    out()
    out(
        "SOURCE GPS:",
        tuple(
            sorted(
                LOCKED_GROUPS.keys()
            )
        )
    )

    out(
        "TOTAL SPLIT RAWS:",
        sum(
            len(v)
            for v in SPLIT_RAWS.values()
        )
    )

    out(
        "TARGET GROUPS:",
        len(results)
    )

    safe_groups = 0
    blocked_groups = 0

    for gp_id in sorted(by_gp):

        out()
        out("#" * 155)
        out(
            "SOURCE GP{}".format(
                gp_id
            )
        )
        out("#" * 155)

        for result in by_gp[gp_id]:

            out()
            out("-" * 155)

            out(
                "GROUP:",
                result["group_name"]
            )

            out(
                "RAW IDS:",
                [
                    x["raw_id"]
                    for x in result["items"]
                ]
            )

            out(
                "SEED RAW:",
                result["seed_raw"]
            )

            out(
                "SEED IDENTITY SOURCE:",
                result["seed_identity_source"]
            )

            out(
                "SEED IDENTITY KEY:",
                result["seed_identity_key"]
            )

            if result["safe"]:
                safe_groups += 1
                out(
                    "SAFE_TO_CREATE_TARGET_CANONICAL: YES"
                )
            else:
                blocked_groups += 1
                out(
                    "SAFE_TO_CREATE_TARGET_CANONICAL: NO"
                )

            out(
                "REASONS:"
            )

            if result["reasons"]:
                for reason in result["reasons"]:
                    out(
                        " -",
                        reason
                    )
            else:
                out(
                    " - explicit approved grouping with unique target identity"
                )

            out()
            out("MEMBERS")

            for item in result["items"]:

                out(
                    " RAW{} | {} | {} | V{} | RAM={} STORAGE={} | MODEL={!r}".format(
                        item["raw_id"],
                        item["store"],
                        item["status"],
                        item["source_variant"],
                        item["ram"],
                        item["storage"],
                        item["model_code"],
                    )
                )

                out(
                    "   TITLE:",
                    item["title"]
                )

                out(
                    "   SOURCE:",
                    item["identity_source"]
                )

                out(
                    "   KEY:",
                    item["identity_key"]
                )

                out(
                    "   OFFERS:",
                    item["offer_ids"]
                )

                out(
                    "   HISTORY:",
                    item["history_ids"]
                )

    out()
    out("=" * 155)
    out("SUMMARY")
    out("=" * 155)

    out(
        "TOTAL GROUPS:",
        len(results)
    )

    out(
        "SAFE GROUPS:",
        safe_groups
    )

    out(
        "BLOCKED/MANUAL GROUPS:",
        blocked_groups
    )

    out()
    out(
        "DATABASE UNCHANGED"
    )

    out("=" * 155)


db.close()

print("SPLIT GROUP BUILDER TAMAMLANDI")
print("FILE:", OUT)
print(
    "TOTAL GROUPS:",
    len(results)
)

print(
    "SAFE GROUPS:",
    sum(
        1
        for x in results
        if x["safe"]
    )
)

print(
    "BLOCKED/MANUAL GROUPS:",
    sum(
        1
        for x in results
        if not x["safe"]
    )
)

print(
    "DATABASE UNCHANGED"
)
