
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
    / "v236361-drift-classifier-result.txt"
)

db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True
)

db.row_factory = sqlite3.Row


def load_specs(value):
    if not value:
        return {}

    try:
        obj = json.loads(value)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def parse_source(source):
    result = {}

    if not source:
        return result

    if ":" in source:
        prefix, body = source.split(":", 1)
    else:
        prefix, body = "", source

    result["_prefix"] = prefix

    for part in body.split("|"):

        if "=" not in part:
            continue

        key, value = part.split("=", 1)

        result[
            key.strip().lower()
        ] = value.strip().lower()

    return result


def clean_family(value):
    return re.sub(
        r"\s+",
        " ",
        (value or "").strip().lower()
    )


def gpu_only_family(family):
    family = clean_family(family)

    return bool(
        re.fullmatch(
            r"(?:rtx|gtx)\s*\d{3,4}"
            r"(?:ti|super)?"
            r"|rx\s*\d{3,4}"
            r"(?:xt|gre)?",
            family.replace(" ", "")
        )
    )


def suspicious_model_code(value):
    value = (value or "").lower().strip()

    if not value:
        return False

    patterns = (
        r"hafizasi\d+",
        r"tipi[a-z0-9]+",
        r"cozunurluk\d+",
        r"agirligi\d+",
        r"\d+(?:[.,]\d+)?(?:mb|gb)/s",
        r"\d+(?:[.,]\d+)?ghz[-/a-z0-9]+",
    )

    return any(
        re.fullmatch(p, value)
        for p in patterns
    )


rows = db.execute("""
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

    gp.identity_key AS gp_identity_key,
    gp.identity_source AS gp_identity_source,
    gp.canonical_name,
    gp.family AS gp_family,
    gp.ram_gb AS gp_ram,
    gp.storage_gb AS gp_storage,
    gp.model_code AS gp_model_code,
    gp.status

FROM raw_products rp

JOIN global_products gp
  ON gp.id=rp.global_product_id

WHERE gp.status='ACTIVE'

ORDER BY rp.id
""").fetchall()


records = []
errors = []


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

    try:
        parsed = S.parse(product)
        explained = S.explain(product)

    except Exception as exc:

        errors.append({
            "raw_id": r["raw_id"],
            "gp": r["global_product_id"],
            "store": r["store_code"],
            "error": str(exc),
            "title": r["title_raw"],
        })

        continue

    new_source = explained.get(
        "identity_source"
    )

    new_key = explained.get(
        "identity_key"
    )

    old_source = r["gp_identity_source"]

    # Current RAW and GP are already ownership-consistent?
    raw_gp_same = (
        r["raw_identity_key"]
        == r["gp_identity_key"]
    )

    # Parser already agrees with canonical?
    parser_same = (
        new_key == r["gp_identity_key"]
        and new_source == old_source
    )

    if parser_same:
        continue

    old = parse_source(old_source)
    new = parse_source(new_source)

    old_semantic = {
        k: v
        for k, v in old.items()
        if k != "_prefix"
    }

    new_semantic = {
        k: v
        for k, v in new.items()
        if k != "_prefix"
    }

    categories = []
    risks = []

    # ------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------

    if (
        old_semantic == new_semantic
        and old.get("_prefix") != new.get("_prefix")
    ):
        categories.append(
            "NAMESPACE_ONLY_V2_TO_V3"
        )

    else:

        old_family = old.get("family")
        new_family = new.get("family")

        if old_family != new_family:
            categories.append(
                "FAMILY_CHANGED"
            )

        if old.get("ram") != new.get("ram"):
            categories.append(
                "RAM_CHANGED"
            )

        if old.get("storage") != new.get("storage"):
            categories.append(
                "STORAGE_CHANGED"
            )

        if old.get("network") != new.get("network"):
            categories.append(
                "NETWORK_CHANGED"
            )

        if old.get("screen") != new.get("screen"):
            categories.append(
                "SCREEN_CHANGED"
            )

        old_extra = {
            k: v
            for k, v in old_semantic.items()
            if k not in (
                "brand",
                "family",
                "ram",
                "storage",
                "network",
                "screen",
            )
        }

        new_extra = {
            k: v
            for k, v in new_semantic.items()
            if k not in (
                "brand",
                "family",
                "ram",
                "storage",
                "network",
                "screen",
            )
        }

        if old_extra != new_extra:
            categories.append(
                "OTHER_IDENTITY_FIELDS_CHANGED"
            )

        if not categories:
            categories.append(
                "KEY_OR_FORMAT_ONLY"
            )

    # ------------------------------------------------------------
    # Risk rules
    # ------------------------------------------------------------

    if (
        old.get("storage")
        and not new.get("storage")
    ):
        risks.append(
            "STORAGE_DISAPPEARED"
        )

    if (
        old.get("ram")
        and not new.get("ram")
    ):
        risks.append(
            "RAM_DISAPPEARED"
        )

    if (
        not old.get("screen")
        and new.get("screen")
    ):
        risks.append(
            "SCREEN_APPEARED"
        )

    if (
        old.get("network")
        != new.get("network")
        and new.get("network")
    ):
        risks.append(
            "NETWORK_BECAME_IDENTITY_SIGNIFICANT"
        )

    if gpu_only_family(
        parsed.family
    ):
        risks.append(
            "FAMILY_COLLAPSED_TO_GPU"
        )

    if suspicious_model_code(
        parsed.model_code
    ):
        risks.append(
            "SUSPICIOUS_MODEL_CODE"
        )

    # Current DB family had something meaningful but parser family
    # became very short / generic.
    old_family_text = clean_family(
        r["gp_family"]
        or old.get("family")
    )

    new_family_text = clean_family(
        parsed.family
    )

    if (
        len(old_family_text) >= 12
        and len(new_family_text) <= 10
        and old_family_text != new_family_text
    ):
        risks.append(
            "FAMILY_COLLAPSED_HEAVILY"
        )

    # Capacity mismatch against stored canonical values.
    if (
        r["gp_storage"] is not None
        and parsed.storage_gb is None
    ):
        risks.append(
            "CANONICAL_STORAGE_LOST"
        )

    if (
        r["gp_ram"] is not None
        and parsed.ram_gb is None
    ):
        risks.append(
            "CANONICAL_RAM_LOST"
        )

    # Positive fixes worth separating from regressions.
    positive = []

    if (
        r["gp_ram"] is not None
        and parsed.ram_gb is None
        and r["global_product_id"] == 41
    ):
        positive.append(
            "KNOWN_SSD_FALSE_RAM_FIX"
        )

    if (
        r["global_product_id"] == 182
        and parsed.network == "5g"
    ):
        positive.append(
            "KNOWN_A07_5G_BOUNDARY"
        )

    records.append({
        "raw_id": r["raw_id"],
        "gp": r["global_product_id"],
        "variant": r["global_variant_id"],
        "store": r["store_code"],
        "title": r["title_raw"],

        "raw_gp_same": raw_gp_same,

        "old_key": r["gp_identity_key"],
        "new_key": new_key,

        "old_source": old_source,
        "new_source": new_source,

        "old_family": (
            r["gp_family"]
            or old.get("family")
        ),
        "new_family": parsed.family,

        "old_ram": r["gp_ram"],
        "new_ram": parsed.ram_gb,

        "old_storage": r["gp_storage"],
        "new_storage": parsed.storage_gb,

        "new_network": parsed.network,
        "new_model_code": parsed.model_code,

        "categories": categories,
        "risks": sorted(set(risks)),
        "positive": positive,
    })


category_counts = Counter()

risk_counts = Counter()

gp_risk_counts = Counter()

namespace_only = []

safe_candidates = []

review_required = []


for x in records:

    for category in x["categories"]:
        category_counts[category] += 1

    for risk in x["risks"]:
        risk_counts[risk] += 1

    if x["risks"]:
        gp_risk_counts[x["gp"]] += 1

    if (
        x["categories"]
        == ["NAMESPACE_ONLY_V2_TO_V3"]
        and not x["risks"]
    ):
        namespace_only.append(x)

    elif not x["risks"]:
        safe_candidates.append(x)

    else:
        review_required.append(x)


with OUT.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as f:

    def out(*args):
        print(*args, file=f)

    out("=" * 140)
    out("V23.63.61 GLOBAL IDENTITY DRIFT CLASSIFIER")
    out("READ ONLY - NO DATABASE WRITES")
    out("=" * 140)

    out()
    out("ACTIVE RAW           :", len(rows))
    out("DRIFT RECORDS        :", len(records))
    out("PARSER ERRORS        :", len(errors))
    out(
        "NAMESPACE ONLY      :",
        len(namespace_only)
    )
    out(
        "NON-RISK CANDIDATES :",
        len(safe_candidates)
    )
    out(
        "REVIEW REQUIRED     :",
        len(review_required)
    )

    out()
    out("=" * 140)
    out("CATEGORY COUNTS")
    out("=" * 140)

    for name, count in category_counts.most_common():
        out(
            "{:<40} {}".format(
                name,
                count
            )
        )

    out()
    out("=" * 140)
    out("RISK COUNTS")
    out("=" * 140)

    if risk_counts:
        for name, count in risk_counts.most_common():
            out(
                "{:<40} {}".format(
                    name,
                    count
                )
            )
    else:
        out("NONE")

    out()
    out("=" * 140)
    out("GLOBAL PRODUCTS WITH MOST RISKY RAW RECORDS")
    out("=" * 140)

    for gp_id, count in sorted(
        gp_risk_counts.items(),
        key=lambda item: (-item[1], item[0])
    ):
        out(
            "GP{} RISKY_RAW={}".format(
                gp_id,
                count
            )
        )

    out()
    out("=" * 140)
    out("NAMESPACE-ONLY SAMPLE")
    out("=" * 140)

    for x in namespace_only[:30]:

        out()
        out(
            "RAW{} | {} | GP{}".format(
                x["raw_id"],
                x["store"],
                x["gp"]
            )
        )

        out(
            "OLD:",
            x["old_source"]
        )

        out(
            "NEW:",
            x["new_source"]
        )

    out()
    out("=" * 140)
    out("REVIEW REQUIRED - FULL DETAIL")
    out("=" * 140)

    for x in review_required:

        out()
        out("-" * 140)

        out(
            "RAW{} | {} | GP{} | V{}".format(
                x["raw_id"],
                x["store"],
                x["gp"],
                x["variant"]
            )
        )

        out("TITLE:")
        out(x["title"])

        out()
        out(
            "CATEGORIES:",
            x["categories"]
        )

        out(
            "RISKS:",
            x["risks"]
        )

        if x["positive"]:
            out(
                "POSITIVE:",
                x["positive"]
            )

        out()
        out(
            "OLD SOURCE:",
            x["old_source"]
        )

        out(
            "NEW SOURCE:",
            x["new_source"]
        )

        out()
        out(
            "OLD FAMILY :",
            x["old_family"]
        )

        out(
            "NEW FAMILY :",
            x["new_family"]
        )

        out(
            "RAM        :",
            x["old_ram"],
            "->",
            x["new_ram"]
        )

        out(
            "STORAGE    :",
            x["old_storage"],
            "->",
            x["new_storage"]
        )

        out(
            "NETWORK    :",
            x["new_network"]
        )

        out(
            "MODEL CODE :",
            x["new_model_code"]
        )

    out()
    out("=" * 140)
    out("NON-RISK SEMANTIC CHANGES")
    out("=" * 140)

    for x in safe_candidates:

        out()
        out(
            "RAW{} | {} | GP{}".format(
                x["raw_id"],
                x["store"],
                x["gp"]
            )
        )

        out(
            "CATEGORIES:",
            x["categories"]
        )

        out(
            "OLD:",
            x["old_source"]
        )

        out(
            "NEW:",
            x["new_source"]
        )

    if errors:

        out()
        out("=" * 140)
        out("PARSER ERRORS")
        out("=" * 140)

        for x in errors:

            out(
                "RAW{} | GP{} | {} | {}".format(
                    x["raw_id"],
                    x["gp"],
                    x["store"],
                    x["error"]
                )
            )

    out()
    out("=" * 140)
    out("CLASSIFIER COMPLETE - DATABASE UNCHANGED")
    out("=" * 140)


db.close()

print("CLASSIFIER TAMAMLANDI")
print("FILE:", OUT)
print("ACTIVE RAW:", len(rows))
print("DRIFT:", len(records))
print("NAMESPACE ONLY:", len(namespace_only))
print("NON-RISK:", len(safe_candidates))
print("REVIEW REQUIRED:", len(review_required))
print("ERROR:", len(errors))
