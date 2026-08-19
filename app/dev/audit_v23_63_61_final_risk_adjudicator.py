
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
    / "v236361-final-risk-adjudicator.txt"
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

        k, v = part.split("=", 1)

        result[
            k.strip().lower()
        ] = v.strip().lower()

    return result


def title_has_ram(title):
    t = S._ascii_fold(title or "").lower()

    patterns = (
        r"\b(?:2|3|4|6|8|12|16|18|24|32|36|48|64)\s*gb\s*ram\b",
        r"\bram\s*[:=-]?\s*(?:2|3|4|6|8|12|16|18|24|32|36|48|64)\s*gb\b",
        r"\b(?:4|6|8|12|16|24|32|36|48|64)\s*gb/"
        r"(?:64|128|256|512|1024|2048)\s*gb\b",
    )

    return any(
        re.search(p, t, re.I)
        for p in patterns
    )


def title_has_storage(title):
    t = S._ascii_fold(title or "").lower()

    patterns = (
        r"\b\d+(?:[.,]\d+)?\s*tb\b",
        r"\b(?:32|64|120|128|240|250|256|480|500|512|960|1000|1024|2048|4096)\s*gb\b",
        r"\b(?:ssd|nvme|depolama|hafiza)\b",
    )

    return any(
        re.search(p, t, re.I)
        for p in patterns
    )


def title_has_screen(title):
    t = S._ascii_fold(title or "").lower()

    return bool(
        re.search(
            r'(?<!\d)\d{1,2}(?:[.,]\d)?\s*(?:inc|inch|")',
            t,
            re.I
        )
    )


def is_phone(parsed):
    family = (parsed.family or "").lower()
    brand = (parsed.brand or "").lower()

    phone_families = (
        "iphone",
        "galaxy",
        "redmi",
        "fold",
        "flip",
        "era",
    )

    return (
        any(x in family for x in phone_families)
        or brand in (
            "apple",
            "samsung",
            "xiaomi",
            "general mobile",
        )
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


results = []
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
        errors.append((
            r["raw_id"],
            r["global_product_id"],
            r["store_code"],
            str(exc),
        ))
        continue

    new_source = explained.get(
        "identity_source"
    )

    new_key = explained.get(
        "identity_key"
    )

    old_source = r["gp_identity_source"]

    if (
        new_source == old_source
        and new_key == r["gp_identity_key"]
    ):
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

    verdict = None
    reasons = []

    # =========================================================
    # 1. EXPECTED FIX
    # =========================================================

    # Known false RAM from SSD throughput.
    if (
        r["global_product_id"] == 41
        and r["gp_ram"] is not None
        and parsed.ram_gb is None
        and parsed.storage_gb == r["gp_storage"]
    ):
        verdict = "EXPECTED_FIX"
        reasons.append(
            "known SSD throughput false-RAM removal"
        )

    # =========================================================
    # 2. V3 POLICY CHANGE
    # =========================================================

    if verdict is None:

        # Parser still sees RAM, but v3 source intentionally excludes it
        # for phone identity.
        if (
            is_phone(parsed)
            and r["gp_ram"] is not None
            and parsed.ram_gb == r["gp_ram"]
            and old.get("ram")
            and not new.get("ram")
        ):
            verdict = "V3_POLICY_CHANGE"
            reasons.append(
                "phone RAM parsed correctly but excluded from v3 canonical identity"
            )

        # Network marketed boundary introduced while capacities remain stable.
        elif (
            is_phone(parsed)
            and old.get("network") != new.get("network")
            and new.get("network")
            and parsed.storage_gb == r["gp_storage"]
        ):
            verdict = "V3_POLICY_CHANGE"
            reasons.append(
                "marketed network became canonical-significant"
            )

        # Pure namespace change.
        elif (
            old_semantic == new_semantic
            and old.get("_prefix") != new.get("_prefix")
        ):
            verdict = "V3_POLICY_CHANGE"
            reasons.append(
                "identity namespace only"
            )

    # =========================================================
    # 3. SOURCE DATA INSUFFICIENT
    # =========================================================

    if verdict is None:

        # Canonical had a value but current raw title does not carry it.
        if (
            r["gp_storage"] is not None
            and parsed.storage_gb is None
            and not title_has_storage(r["title_raw"])
        ):
            verdict = "SOURCE_DATA_INSUFFICIENT"
            reasons.append(
                "canonical storage absent from current raw title"
            )

        elif (
            r["gp_ram"] is not None
            and parsed.ram_gb is None
            and not title_has_ram(r["title_raw"])
        ):
            verdict = "SOURCE_DATA_INSUFFICIENT"
            reasons.append(
                "canonical RAM absent from current raw title"
            )

    # =========================================================
    # 4. REAL PARSER REGRESSION
    # =========================================================

    if verdict is None:

        if (
            title_has_ram(r["title_raw"])
            and parsed.ram_gb is None
        ):
            verdict = "REAL_PARSER_REGRESSION"
            reasons.append(
                "explicit RAM present in title but parser returned None"
            )

        elif (
            title_has_storage(r["title_raw"])
            and parsed.storage_gb is None
        ):
            verdict = "REAL_PARSER_REGRESSION"
            reasons.append(
                "explicit storage present in title but parser returned None"
            )

        elif (
            parsed.screen_inch is not None
            and not title_has_screen(r["title_raw"])
            and old.get("screen") != new.get("screen")
        ):
            verdict = "REAL_PARSER_REGRESSION"
            reasons.append(
                "screen appeared without explicit screen evidence in title"
            )

    # =========================================================
    # 5. FAMILY CHANGES
    # =========================================================

    if verdict is None:

        old_family = (
            r["gp_family"]
            or old.get("family")
            or ""
        ).strip().lower()

        new_family = (
            parsed.family
            or ""
        ).strip().lower()

        if old_family != new_family:

            # Compact strong model family can be an improvement,
            # but not safe enough to auto-approve.
            if (
                parsed.model_code
                and new_family == parsed.model_code.lower()
                and len(new_family) >= 5
            ):
                verdict = "NEEDS_MANUAL_REVIEW"
                reasons.append(
                    "family compacted to strong model-code candidate"
                )

            else:
                verdict = "NEEDS_MANUAL_REVIEW"
                reasons.append(
                    "semantic family changed"
                )

    # =========================================================
    # 6. Catch remaining semantic drift
    # =========================================================

    if verdict is None:

        if old_semantic != new_semantic:
            verdict = "NEEDS_MANUAL_REVIEW"
            reasons.append(
                "remaining semantic identity drift"
            )

        else:
            verdict = "V3_POLICY_CHANGE"
            reasons.append(
                "format/hash/namespace drift only"
            )


    results.append({
        "raw_id": r["raw_id"],
        "gp": r["global_product_id"],
        "variant": r["global_variant_id"],
        "store": r["store_code"],
        "title": r["title_raw"],

        "verdict": verdict,
        "reasons": reasons,

        "old_source": old_source,
        "new_source": new_source,

        "old_ram": r["gp_ram"],
        "new_ram": parsed.ram_gb,

        "old_storage": r["gp_storage"],
        "new_storage": parsed.storage_gb,

        "old_family": r["gp_family"],
        "new_family": parsed.family,

        "screen": parsed.screen_inch,
        "network": parsed.network,
        "model_code": parsed.model_code,
    })


counts = Counter(
    x["verdict"]
    for x in results
)

gp_real_bug = Counter(
    x["gp"]
    for x in results
    if x["verdict"] == "REAL_PARSER_REGRESSION"
)


with OUT.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as f:

    def out(*args):
        print(*args, file=f)

    out("=" * 140)
    out("V23.63.61 FINAL RISK ADJUDICATOR")
    out("READ ONLY - NO DATABASE WRITES")
    out("=" * 140)

    out()
    out("ACTIVE RAW:", len(rows))
    out("DRIFT ANALYZED:", len(results))
    out("PARSER ERRORS:", len(errors))

    out()
    out("=" * 140)
    out("VERDICT COUNTS")
    out("=" * 140)

    for name in (
        "REAL_PARSER_REGRESSION",
        "V3_POLICY_CHANGE",
        "EXPECTED_FIX",
        "SOURCE_DATA_INSUFFICIENT",
        "NEEDS_MANUAL_REVIEW",
    ):
        out(
            "{:<28} {}".format(
                name,
                counts.get(name, 0)
            )
        )

    out()
    out("=" * 140)
    out("REAL PARSER REGRESSION - FULL DETAIL")
    out("=" * 140)

    real = [
        x
        for x in results
        if x["verdict"] == "REAL_PARSER_REGRESSION"
    ]

    if not real:
        out("NONE")

    for x in real:

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
            "REASONS:",
            x["reasons"]
        )

        out(
            "RAM:",
            x["old_ram"],
            "->",
            x["new_ram"]
        )

        out(
            "STORAGE:",
            x["old_storage"],
            "->",
            x["new_storage"]
        )

        out(
            "SCREEN:",
            x["screen"]
        )

        out(
            "NETWORK:",
            x["network"]
        )

        out(
            "MODEL CODE:",
            x["model_code"]
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
    out("=" * 140)
    out("NEEDS MANUAL REVIEW - FULL DETAIL")
    out("=" * 140)

    manual = [
        x
        for x in results
        if x["verdict"] == "NEEDS_MANUAL_REVIEW"
    ]

    if not manual:
        out("NONE")

    for x in manual:

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

        out(
            "REASONS:",
            x["reasons"]
        )

        out(
            "FAMILY:",
            x["old_family"],
            "->",
            x["new_family"]
        )

        out(
            "RAM:",
            x["old_ram"],
            "->",
            x["new_ram"]
        )

        out(
            "STORAGE:",
            x["old_storage"],
            "->",
            x["new_storage"]
        )

        out(
            "SCREEN:",
            x["screen"]
        )

        out(
            "MODEL CODE:",
            x["model_code"]
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
    out("=" * 140)
    out("SOURCE DATA INSUFFICIENT")
    out("=" * 140)

    for x in results:
        if x["verdict"] != "SOURCE_DATA_INSUFFICIENT":
            continue

        out()
        out(
            "RAW{} | {} | GP{} | {}".format(
                x["raw_id"],
                x["store"],
                x["gp"],
                x["reasons"]
            )
        )
        out(
            "TITLE:",
            x["title"]
        )

    out()
    out("=" * 140)
    out("EXPECTED FIX")
    out("=" * 140)

    for x in results:
        if x["verdict"] != "EXPECTED_FIX":
            continue

        out()
        out(
            "RAW{} | GP{} | {}".format(
                x["raw_id"],
                x["gp"],
                x["reasons"]
            )
        )

    out()
    out("=" * 140)
    out("V3 POLICY CHANGE SUMMARY")
    out("=" * 140)

    policy_gp = Counter(
        x["gp"]
        for x in results
        if x["verdict"] == "V3_POLICY_CHANGE"
    )

    for gp_id, count in sorted(
        policy_gp.items(),
        key=lambda item: (-item[1], item[0])
    ):
        out(
            "GP{} RECORDS={}".format(
                gp_id,
                count
            )
        )

    if errors:

        out()
        out("=" * 140)
        out("PARSER ERRORS")
        out("=" * 140)

        for row in errors:
            out(row)

    out()
    out("=" * 140)
    out("ADJUDICATOR COMPLETE - DATABASE UNCHANGED")
    out("=" * 140)


db.close()

print("ADJUDICATOR TAMAMLANDI")
print("FILE:", OUT)
print("ACTIVE RAW:", len(rows))
print("DRIFT ANALYZED:", len(results))

for name in (
    "REAL_PARSER_REGRESSION",
    "V3_POLICY_CHANGE",
    "EXPECTED_FIX",
    "SOURCE_DATA_INSUFFICIENT",
    "NEEDS_MANUAL_REVIEW",
):
    print(
        name + ":",
        counts.get(name, 0)
    )

print("ERROR:", len(errors))
