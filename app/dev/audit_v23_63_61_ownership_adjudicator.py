
import sys
import json
import re
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from collections import Counter, defaultdict

ROOT = Path.cwd()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

DB = ROOT / "data" / "products.db"

OUT = (
    Path.home()
    / "Downloads"
    / "v236361-ownership-adjudicator-result.txt"
)

# GP'ler ?nceki ownership audit'ten gelen explicit scope.
TARGET_GPS = (
    12, 16, 18, 22, 29,
    39, 51, 68, 78, 120,
    124, 125, 134, 142, 144,
    154, 160, 173, 179, 180,
)


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


def model_tokens(text):
    """
    Conservative strong identity hints only.
    We deliberately avoid generic CPU/GPU numbers.
    """
    t = norm(text)

    patterns = (
        r"\b[a-z]\d{2,4}[a-z0-9._/-]{2,}\b",
        r"\b\d{2}[a-z]{2}\d{3,}[a-z0-9]*\b",
        r"\b(?:mh[a-z0-9]{4,}|z1[a-z0-9]{5,})/?[a-z]*\b",
        r"\b(?:s100\.[a-z0-9._/-]+)\b",
        r"\b(?:82[a-z0-9]{6,})\b",
        r"\b(?:83[a-z0-9]{6,})\b",
        r"\b(?:fx[a-z0-9-]{5,})\b",
        r"\b(?:pb[a-z0-9]{5,})\b",
    )

    out = set()

    for p in patterns:
        out.update(
            m.group(0)
            for m in re.finditer(
                p,
                t,
                re.I
            )
        )

    return sorted(out)


def explicit_family_markers(text):
    t = norm(text)

    markers = []

    families = (
        "abra a5",
        "abra a7",
        "tulpar t6",
        "ideapad slim 3",
        "loq",
        "nirvana s100",
        "iphone 15",
        "iphone 17 pro max",
        "ipad a16",
        "macbook neo",
        "freebuds se 2",
        "watch d2",
        "redmi",
        "sword x55",
        "sword x60",
        "attack shark x11 se",
        "attack shark x11 superlight",
    )

    for family in families:
        if family in t:
            markers.append(family)

    return markers


db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True
)

db.row_factory = sqlite3.Row

placeholders = ",".join(
    "?"
    for _ in TARGET_GPS
)

rows = db.execute(
    f"""
    SELECT
        rp.id AS raw_id,
        rp.store_code,
        rp.store_product_id,
        rp.title_raw,
        rp.brand_raw,
        rp.model_raw,
        rp.description_raw,
        rp.specifications_raw,
        rp.category_raw,
        rp.identity_key AS raw_identity_key,
        rp.global_product_id,
        rp.global_variant_id,
        rp.reconciliation_status,

        gp.identity_key AS gp_identity_key,
        gp.identity_source,
        gp.canonical_name,
        gp.normalized_brand,
        gp.family AS gp_family,
        gp.ram_gb AS gp_ram,
        gp.storage_gb AS gp_storage,
        gp.status,
        gp.raw_product_count,
        gp.active_offer_count

    FROM raw_products rp

    JOIN global_products gp
      ON gp.id=rp.global_product_id

    WHERE rp.global_product_id IN ({placeholders})

    ORDER BY
        rp.global_product_id,
        rp.id
    """,
    TARGET_GPS,
).fetchall()


groups = defaultdict(list)


for r in rows:

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

    groups[
        r["global_product_id"]
    ].append({
        "raw_id": r["raw_id"],
        "store": r["store_code"],
        "title": r["title_raw"],
        "variant_id": r["global_variant_id"],
        "status": r["reconciliation_status"],

        "brand": parsed.brand,
        "family": parsed.family,
        "variant": parsed.variant,
        "ram": parsed.ram_gb,
        "storage": parsed.storage_gb,
        "network": parsed.network,
        "model_code": parsed.model_code,

        "source": explained.get(
            "identity_source"
        ),
        "key": explained.get(
            "identity_key"
        ),

        "current_gp_key": r["gp_identity_key"],

        "canonical_name": r["canonical_name"],
        "canonical_brand": r["normalized_brand"],
        "canonical_family": r["gp_family"],
        "canonical_ram": r["gp_ram"],
        "canonical_storage": r["gp_storage"],

        "strong_tokens": model_tokens(
            " ".join(
                [
                    r["title_raw"] or "",
                    r["model_raw"] or "",
                    r["store_product_id"] or "",
                ]
            )
        ),

        "family_markers": explicit_family_markers(
            r["title_raw"]
        ),
    })


# ------------------------------------------------------------------
# Explicit evidence locks from already audited cases.
# This is classification only ? no DB mutation.
# ------------------------------------------------------------------

CONFIRMED_RULES = {
    51: {
        "verdict": "CONFIRMED_COLLISION",
        "reason": (
            "Tulpar canonical contains Abra A5/A7 raw products"
        ),
    },

    29: {
        "verdict": "CONFIRMED_COLLISION",
        "reason": (
            "multiple Nirvana S100 CPU/RAM/storage/SKU configurations"
        ),
    },

    120: {
        "verdict": "CONFIRMED_COLLISION",
        "reason": (
            "multiple Lenovo LOQ SKU/CPU/GPU configurations"
        ),
    },

    154: {
        "verdict": "CONFIRMED_COLLISION",
        "reason": (
            "IdeaPad Slim 3 canonical contains materially different CPU/model configuration"
        ),
    },

    173: {
        "verdict": "CONFIRMED_COLLISION",
        "reason": (
            "Sword X55 canonical contains Sword X60 member"
        ),
    },

    12: {
        "verdict": "CONFIRMED_COLLISION",
        "reason": (
            "Attack Shark X11 SE and X11 Superlight are distinct marketed models"
        ),
    },

    134: {
        "verdict": "SINGLE_BAD_MEMBER",
        "reason": (
            "iPhone 17 Pro Max canonical contains an iPad A16 raw member"
        ),
    },

    160: {
        "verdict": "SINGLE_BAD_MEMBER",
        "reason": (
            "FreeBuds SE 2 canonical contains Huawei Watch D2 + FreeBuds bundle member"
        ),
    },

    16: {
        "verdict": "SAME_PRODUCT_ALIAS_DRIFT",
        "reason": (
            "same Lenovo IdeaPad Slim 3 identity anchored by shared 82XB009GTX evidence"
        ),
    },

    78: {
        "verdict": "SAME_PRODUCT_ALIAS_DRIFT",
        "reason": (
            "same iPhone 15 family; parser-source difference mainly missing source capacity evidence"
        ),
    },

    144: {
        "verdict": "SAME_PRODUCT_ALIAS_DRIFT",
        "reason": (
            "Redmi 20000 / PB200LZM appear to be same marketed powerbank identity"
        ),
    },

    124: {
        "verdict": "VARIANT_LEVEL_DIFFERENCE",
        "reason": (
            "MacBook Neo A18 Pro 8/256 members share base product but expose SKU/color-level codes"
        ),
    },
}


def auto_verdict(gp_id, items):

    if gp_id in CONFIRMED_RULES:
        return (
            CONFIRMED_RULES[gp_id]["verdict"],
            CONFIRMED_RULES[gp_id]["reason"],
        )

    brands = {
        x["brand"]
        for x in items
        if x["brand"]
    }

    families = {
        norm(x["family"])
        for x in items
        if x["family"]
    }

    strong_token_sets = [
        set(x["strong_tokens"])
        for x in items
        if x["strong_tokens"]
    ]

    # Different parser brands under one canonical: fail closed.
    if len(brands) > 1:
        return (
            "SOURCE_CONTAMINATION",
            "multiple normalized brands under one canonical",
        )

    # Single outlier family among otherwise dominant family.
    counts = Counter(
        norm(x["family"])
        for x in items
        if x["family"]
    )

    if counts:

        dominant, dominant_count = counts.most_common(1)[0]

        if (
            dominant_count >= 2
            and dominant_count == len(items) - 1
        ):
            return (
                "SINGLE_BAD_MEMBER",
                "one parser-family outlier against dominant canonical membership",
            )

    # If all records share at least one strong SKU/model token,
    # parser-family formatting drift should not trigger split.
    if strong_token_sets:

        common = set.intersection(
            *strong_token_sets
        )

        if common:
            return (
                "SAME_PRODUCT_ALIAS_DRIFT",
                "members share strong SKU/model token: {}".format(
                    sorted(common)
                ),
            )

    if len(families) > 1:
        return (
            "MANUAL_REVIEW",
            "multiple parser families without sufficient strong split evidence",
        )

    return (
        "SAME_PRODUCT_ALIAS_DRIFT",
        "single semantic family with parser formatting/source drift",
    )


results = []


for gp_id in TARGET_GPS:

    items = groups.get(
        gp_id,
        []
    )

    if not items:
        results.append({
            "gp": gp_id,
            "verdict": "MANUAL_REVIEW",
            "reason": "target GP has no raw members",
            "items": [],
        })
        continue

    verdict, reason = auto_verdict(
        gp_id,
        items
    )

    results.append({
        "gp": gp_id,
        "verdict": verdict,
        "reason": reason,
        "items": items,
    })


# ------------------------------------------------------------------
# Raw-level candidate split grouping for confirmed collision GPs.
# These are suggestions only.
# ------------------------------------------------------------------

def group_key(item):

    markers = item["family_markers"]

    if markers:
        return "|".join(
            sorted(markers)
        )

    if item["model_code"]:
        return (
            "model_code="
            + norm(item["model_code"])
        )

    if item["strong_tokens"]:
        return (
            "strong="
            + ",".join(
                item["strong_tokens"]
            )
        )

    return (
        "family="
        + norm(item["family"])
    )


verdict_counts = Counter(
    x["verdict"]
    for x in results
)


with OUT.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as f:

    def out(*args):
        print(*args, file=f)

    out("=" * 155)
    out("V23.63.61 OWNERSHIP ADJUDICATOR")
    out("READ ONLY - NO DATABASE WRITES")
    out("=" * 155)

    out()
    out(
        "TARGET GPS:",
        len(TARGET_GPS)
    )

    out(
        "RAW MEMBERS ANALYZED:",
        len(rows)
    )

    out()
    out("=" * 155)
    out("VERDICT COUNTS")
    out("=" * 155)

    for name in (
        "CONFIRMED_COLLISION",
        "SINGLE_BAD_MEMBER",
        "SAME_PRODUCT_ALIAS_DRIFT",
        "VARIANT_LEVEL_DIFFERENCE",
        "SOURCE_CONTAMINATION",
        "MANUAL_REVIEW",
    ):
        out(
            "{:<30} {}".format(
                name,
                verdict_counts.get(
                    name,
                    0
                )
            )
        )

    out()
    out("=" * 155)
    out("GP VERDICTS")
    out("=" * 155)

    for result in results:

        out()
        out(
            "GP{} => {}".format(
                result["gp"],
                result["verdict"]
            )
        )

        out(
            "REASON:",
            result["reason"]
        )

        if not result["items"]:
            continue

        first = result["items"][0]

        out(
            "CANONICAL:",
            first["canonical_name"]
        )

        out(
            "RAW COUNT:",
            len(result["items"])
        )

    out()
    out("=" * 155)
    out("CONFIRMED COLLISION - RAW SPLIT CANDIDATES")
    out("=" * 155)

    for result in results:

        if result["verdict"] != "CONFIRMED_COLLISION":
            continue

        gp_id = result["gp"]

        out()
        out("#" * 155)
        out(
            "GP{} CONFIRMED COLLISION".format(
                gp_id
            )
        )
        out("#" * 155)

        buckets = defaultdict(list)

        for item in result["items"]:
            buckets[
                group_key(item)
            ].append(item)

        for key, members in sorted(
            buckets.items(),
            key=lambda kv: (
                -len(kv[1]),
                kv[0]
            )
        ):

            out()
            out(
                "GROUP:",
                key
            )

            out(
                "RAW IDS:",
                [
                    x["raw_id"]
                    for x in members
                ]
            )

            out(
                "VARIANT IDS:",
                sorted(
                    {
                        x["variant_id"]
                        for x in members
                        if x["variant_id"] is not None
                    }
                )
            )

            for x in members:

                out(
                    " RAW{} | {} | {} | RAM={} STORAGE={} | {}".format(
                        x["raw_id"],
                        x["store"],
                        x["status"],
                        x["ram"],
                        x["storage"],
                        x["title"],
                    )
                )

    out()
    out("=" * 155)
    out("SINGLE BAD MEMBERS")
    out("=" * 155)

    for result in results:

        if result["verdict"] != "SINGLE_BAD_MEMBER":
            continue

        items = result["items"]

        family_counts = Counter(
            norm(x["family"])
            for x in items
            if x["family"]
        )

        dominant = None

        if family_counts:
            dominant = family_counts.most_common(1)[0][0]

        out()
        out(
            "GP{} | {}".format(
                result["gp"],
                result["reason"]
            )
        )

        for x in items:

            bad = False

            # Explicit locks for known cases.
            if (
                result["gp"] == 134
                and "ipad a16" in norm(x["family"])
            ):
                bad = True

            elif (
                result["gp"] == 160
                and "watch d2" in norm(x["family"])
            ):
                bad = True

            elif (
                dominant
                and norm(x["family"]) != dominant
            ):
                bad = True

            if bad:
                out(
                    " BAD RAW{} | {} | V{} | {} | {}".format(
                        x["raw_id"],
                        x["store"],
                        x["variant_id"],
                        x["status"],
                        x["title"],
                    )
                )

    out()
    out("=" * 155)
    out("PRESERVE / NO-SPLIT GROUPS")
    out("=" * 155)

    for result in results:

        if result["verdict"] not in (
            "SAME_PRODUCT_ALIAS_DRIFT",
            "VARIANT_LEVEL_DIFFERENCE",
        ):
            continue

        out()
        out(
            "GP{} => {} | {}".format(
                result["gp"],
                result["verdict"],
                result["reason"],
            )
        )

        out(
            "RAW IDS:",
            [
                x["raw_id"]
                for x in result["items"]
            ]
        )

    out()
    out("=" * 155)
    out("MANUAL REVIEW")
    out("=" * 155)

    for result in results:

        if result["verdict"] not in (
            "MANUAL_REVIEW",
            "SOURCE_CONTAMINATION",
        ):
            continue

        out()
        out(
            "GP{} => {} | {}".format(
                result["gp"],
                result["verdict"],
                result["reason"],
            )
        )

        for x in result["items"]:

            out(
                " RAW{} | {} | family={!r} | model={!r} | {}".format(
                    x["raw_id"],
                    x["store"],
                    x["family"],
                    x["model_code"],
                    x["title"],
                )
            )

    out()
    out("=" * 155)
    out("OWNERSHIP ADJUDICATOR COMPLETE - DATABASE UNCHANGED")
    out("=" * 155)


db.close()

print("OWNERSHIP ADJUDICATOR TAMAMLANDI")
print("FILE:", OUT)
print("TARGET GPS:", len(TARGET_GPS))
print("RAW MEMBERS:", len(rows))

for name in (
    "CONFIRMED_COLLISION",
    "SINGLE_BAD_MEMBER",
    "SAME_PRODUCT_ALIAS_DRIFT",
    "VARIANT_LEVEL_DIFFERENCE",
    "SOURCE_CONTAMINATION",
    "MANUAL_REVIEW",
):
    print(
        name + ":",
        verdict_counts.get(name, 0)
    )
