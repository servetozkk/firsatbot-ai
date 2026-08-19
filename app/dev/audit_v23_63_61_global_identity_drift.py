
import sys
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from collections import Counter

ROOT = Path.cwd()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

DB = ROOT / "data" / "products.db"
OUT = Path.home() / "Downloads" / "v236361-global-identity-drift-result.txt"

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
    gp.status

FROM raw_products rp

JOIN global_products gp
  ON gp.id=rp.global_product_id

WHERE gp.status='ACTIVE'

ORDER BY rp.id
""").fetchall()


drifts = []
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

        new_key = explained.get(
            "identity_key"
        )

        new_source = explained.get(
            "identity_source"
        )

    except Exception as exc:

        errors.append({
            "raw_id": r["raw_id"],
            "store": r["store_code"],
            "error": str(exc),
            "title": r["title_raw"],
        })

        continue

    raw_gp_mismatch = (
        r["raw_identity_key"]
        != r["gp_identity_key"]
    )

    parser_gp_mismatch = (
        new_key
        != r["gp_identity_key"]
    )

    parser_raw_mismatch = (
        new_key
        != r["raw_identity_key"]
    )

    source_mismatch = (
        new_source
        != r["gp_identity_source"]
    )

    if (
        raw_gp_mismatch
        or parser_gp_mismatch
        or parser_raw_mismatch
        or source_mismatch
    ):
        drifts.append({
            "raw_id": r["raw_id"],
            "store": r["store_code"],
            "gp": r["global_product_id"],
            "variant": r["global_variant_id"],

            "raw_key": r["raw_identity_key"],
            "gp_key": r["gp_identity_key"],
            "parser_key": new_key,

            "gp_source": r["gp_identity_source"],
            "parser_source": new_source,

            "brand": parsed.brand,
            "family": parsed.family,
            "variant_parsed": parsed.variant,
            "ram": parsed.ram_gb,
            "storage": parsed.storage_gb,
            "network": parsed.network,
            "model_code": parsed.model_code,

            "raw_gp_mismatch": raw_gp_mismatch,
            "parser_gp_mismatch": parser_gp_mismatch,
            "parser_raw_mismatch": parser_raw_mismatch,
            "source_mismatch": source_mismatch,

            "title": r["title_raw"],
        })


counts = Counter()

for x in drifts:
    for field in (
        "raw_gp_mismatch",
        "parser_gp_mismatch",
        "parser_raw_mismatch",
        "source_mismatch",
    ):
        if x[field]:
            counts[field] += 1


with OUT.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as f:

    def out(*args):
        print(*args, file=f)

    out("=" * 130)
    out("V23.63.61 GLOBAL PARSER / CANONICAL IDENTITY DRIFT AUDIT")
    out("READ ONLY")
    out("=" * 130)

    out()
    out("TOTAL ACTIVE RAW :", len(rows))
    out("TOTAL DRIFT      :", len(drifts))
    out("PARSER ERRORS    :", len(errors))

    out()
    out("=" * 130)
    out("DRIFT TYPE COUNTS")
    out("=" * 130)

    for name in (
        "raw_gp_mismatch",
        "parser_gp_mismatch",
        "parser_raw_mismatch",
        "source_mismatch",
    ):
        out(
            "{:<24} {}".format(
                name,
                counts.get(name, 0)
            )
        )

    out()
    out("=" * 130)
    out("DRIFT BY GLOBAL PRODUCT")
    out("=" * 130)

    gp_counts = Counter(
        x["gp"]
        for x in drifts
    )

    for gp_id, count in sorted(
        gp_counts.items(),
        key=lambda item: (-item[1], item[0])
    ):
        out(
            "GP{} DRIFT={}".format(
                gp_id,
                count
            )
        )

    out()
    out("=" * 130)
    out("DRIFT DETAILS")
    out("=" * 130)

    for x in drifts:

        out()
        out("-" * 130)

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
            "CURRENT RAW KEY :",
            x["raw_key"]
        )

        out(
            "CURRENT GP KEY  :",
            x["gp_key"]
        )

        out(
            "PARSER KEY      :",
            x["parser_key"]
        )

        out()
        out(
            "CURRENT SOURCE  :",
            x["gp_source"]
        )

        out(
            "PARSER SOURCE   :",
            x["parser_source"]
        )

        out()
        out(
            "PARSED:",
            (
                x["brand"],
                x["family"],
                x["variant_parsed"],
                x["ram"],
                x["storage"],
                x["network"],
                x["model_code"],
            )
        )

        out(
            "FLAGS:",
            {
                "raw_gp": x["raw_gp_mismatch"],
                "parser_gp": x["parser_gp_mismatch"],
                "parser_raw": x["parser_raw_mismatch"],
                "source": x["source_mismatch"],
            }
        )

    if errors:

        out()
        out("=" * 130)
        out("PARSER ERRORS")
        out("=" * 130)

        for x in errors:
            out(
                "RAW{} | {} | {}".format(
                    x["raw_id"],
                    x["store"],
                    x["error"]
                )
            )
            out(
                "TITLE:",
                x["title"]
            )

    out()
    out("=" * 130)
    out("AUDIT COMPLETE - DATABASE UNCHANGED")
    out("=" * 130)


db.close()

print("AUDIT TAMAMLANDI")
print("FILE:", OUT)
print("ACTIVE RAW:", len(rows))
print("DRIFT:", len(drifts))
print("ERROR:", len(errors))
