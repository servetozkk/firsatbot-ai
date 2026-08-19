
import sys
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

ROOT = Path.cwd()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

DB = ROOT / "data" / "products.db"

OUT = (
    Path.home()
    / "Downloads"
    / "v236361-target-canonical-contracts.txt"
)

# ============================================================
# V23.63.61 TARGET CANONICAL CONTRACTS
#
# READ ONLY.
#
# Important:
# - parser key is evidence, not authority
# - explicit model/SKU wins over noisy family text
# - uncertain/contaminated groups fail closed
# ============================================================

CONTRACTS = [

    {
        "source_gp": 12,
        "group": "x11-se",
        "raws": [348],
        "brand": "attack shark",
        "canonical_model": "x11 se",
        "model_code": "x11se",
        "ram": None,
        "storage": None,
        "decision": "APPROVED",
        "evidence": "explicit marketed model X11 SE",
    },

    {
        "source_gp": 29,
        "group": "s100-1342-bf00x",
        "raws": [344],
        "brand": "casper",
        "canonical_model": "nirvana s100",
        "model_code": "s100.1342-bf00x-g-f",
        "ram": 16,
        "storage": 1024,
        "decision": "APPROVED",
        "evidence": "explicit full SKU",
    },

    {
        "source_gp": 29,
        "group": "s100-1362-cf00x",
        "raws": [345, 346],
        "brand": "casper",
        "canonical_model": "nirvana s100",
        "model_code": "s100.1362-cf00x-g-f",
        "ram": 24,
        "storage": 1024,
        "decision": "APPROVED",
        "evidence": "same explicit full SKU across both RAWs",
    },

    {
        "source_gp": 29,
        "group": "s100-1362-500gb-unknown-sku",
        "raws": [347],
        "brand": "casper",
        "canonical_model": "nirvana s100",
        "model_code": None,
        "ram": 16,
        "storage": 500,
        "decision": "APPROVED_WITHOUT_SKU",
        "evidence": "explicit S100 + i7-13620H + 16GB + 500GB; full SKU unavailable",
    },

    {
        "source_gp": 51,
        "group": "abra-a7-v15.6.4",
        "raws": [16, 227],
        "brand": "monster",
        "canonical_model": "abra a7 v15.6.4",
        "model_code": "v15.6.4",
        "ram": 16,
        "storage": 1024,
        "decision": "APPROVED",
        "evidence": "same explicit marketed model in both titles",
    },

    {
        "source_gp": 51,
        "group": "abra-a5-v21.8.5",
        "raws": [226, 229],
        "brand": "monster",
        "canonical_model": "abra a5 v21.8.5",
        "model_code": "v21.8.5",
        "ram": 32,
        "storage": 1024,
        "decision": "APPROVED",
        "evidence": "same explicit marketed model in both titles",
    },

    {
        "source_gp": 51,
        "group": "manual-raw228",
        "raws": [228],
        "brand": "monster",
        "canonical_model": None,
        "model_code": "v15.6.4",
        "ram": 16,
        "storage": 1024,
        "decision": "BLOCKED",
        "evidence": "insufficient source title for automatic ownership move",
    },

    {
        "source_gp": 120,
        "group": "loq-83s00030trat37",
        "raws": [230],
        "brand": "lenovo",
        "canonical_model": "loq 15arp10e",
        "model_code": "83s00030trat37",
        "ram": 16,
        "storage": 512,
        "decision": "APPROVED",
        "evidence": "explicit Lenovo machine type / SKU",
    },

    {
        "source_gp": 120,
        "group": "loq-83jc000qtra29",
        "raws": [231],
        "brand": "lenovo",
        "canonical_model": "loq",
        "model_code": "83jc000qtra29",
        "ram": 16,
        "storage": 2048,
        "decision": "APPROVED",
        "evidence": "explicit Lenovo machine type / SKU",
    },

    {
        "source_gp": 134,
        "group": "ipad-a16-md4d4tu-a",
        "raws": [321],
        "brand": "apple",
        "canonical_model": "ipad a16",
        "model_code": "md4d4tu/a",
        "ram": 8,
        "storage": 128,
        "decision": "APPROVED",
        "evidence": "explicit Apple part number",
    },

    {
        "source_gp": 154,
        "group": "ideapad-slim3-i5-13420h",
        "raws": [258],
        "brand": "lenovo",
        "canonical_model": "ideapad slim 3",
        "model_code": None,
        "ram": 8,
        "storage": 512,
        "decision": "APPROVED_WITHOUT_SKU",
        "evidence": "explicit marketed family + CPU/RAM/storage",
    },

    {
        "source_gp": 160,
        "group": "watch-d2-freebuds-bundle",
        "raws": [304],
        "brand": "huawei",
        "canonical_model": "watch d2 + freebuds se 2 bundle",
        "model_code": None,
        "ram": None,
        "storage": None,
        "decision": "APPROVED_BUNDLE",
        "evidence": "title explicitly represents a Watch D2 + FreeBuds SE 2 bundle",
    },

    {
        "source_gp": 173,
        "group": "sword-x60",
        "raws": [333],
        "brand": None,
        "canonical_model": "sword x60",
        "model_code": None,
        "ram": 32,
        "storage": 1024,
        "decision": "BLOCKED_SOURCE_CONTAMINATION",
        "evidence": "title says Sword X60 while parsed/source brand says marka xaser and model HSR001362",
    },
]


def specs(value):

    if not value:
        return {}

    try:
        obj = json.loads(value)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True
)

db.row_factory = sqlite3.Row

approved = 0
blocked = 0
errors = 0


with OUT.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as f:

    def out(*args):
        print(*args, file=f)

    out("=" * 150)
    out("V23.63.61 TARGET CANONICAL CONTRACT BUILDER")
    out("READ ONLY - NO DATABASE WRITES")
    out("=" * 150)
    out()

    for contract in CONTRACTS:

        out("-" * 150)

        out(
            "SOURCE GP:",
            contract["source_gp"]
        )

        out(
            "GROUP:",
            contract["group"]
        )

        out(
            "RAW IDS:",
            contract["raws"]
        )

        out(
            "DECISION:",
            contract["decision"]
        )

        out(
            "TARGET BRAND:",
            contract["brand"]
        )

        out(
            "TARGET MODEL:",
            contract["canonical_model"]
        )

        out(
            "TARGET MODEL CODE:",
            contract["model_code"]
        )

        out(
            "TARGET RAM:",
            contract["ram"]
        )

        out(
            "TARGET STORAGE:",
            contract["storage"]
        )

        out(
            "EVIDENCE:",
            contract["evidence"]
        )

        valid = True

        for raw_id in contract["raws"]:

            r = db.execute("""
                SELECT
                    id,
                    global_product_id,
                    title_raw,
                    brand_raw,
                    model_raw,
                    description_raw,
                    specifications_raw,
                    category_raw,
                    store_product_id
                FROM raw_products
                WHERE id=?
            """, (raw_id,)).fetchone()

            if r is None:
                out(
                    "ERROR: RAW{} missing".format(
                        raw_id
                    )
                )
                valid = False
                errors += 1
                continue

            if r["global_product_id"] != contract["source_gp"]:
                out(
                    "ERROR: RAW{} ownership expected GP{} got GP{}".format(
                        raw_id,
                        contract["source_gp"],
                        r["global_product_id"],
                    )
                )
                valid = False
                errors += 1
                continue

            product = SimpleNamespace(
                name=r["title_raw"] or "",
                brand=r["brand_raw"] or "",
                model=r["model_raw"] or "",
                description=r["description_raw"] or "",
                specifications=specs(
                    r["specifications_raw"]
                ),
                category=r["category_raw"] or "",
                product_code=r["store_product_id"] or "",
            )

            parsed = S.parse(product)
            explained = S.explain(product)

            out()
            out(
                " RAW{} TITLE: {}".format(
                    raw_id,
                    r["title_raw"]
                )
            )

            out(
                " RAW{} PARSED: {}".format(
                    raw_id,
                    (
                        parsed.brand,
                        parsed.family,
                        parsed.ram_gb,
                        parsed.storage_gb,
                        parsed.model_code,
                    )
                )
            )

            out(
                " RAW{} PARSER SOURCE: {}".format(
                    raw_id,
                    explained.get(
                        "identity_source"
                    )
                )
            )

        if contract["decision"].startswith(
            "BLOCKED"
        ):
            blocked += 1
            out()
            out(
                "CONTRACT STATE: FAIL-CLOSED"
            )

        elif valid:
            approved += 1
            out()
            out(
                "CONTRACT STATE: APPROVED FOR COPY-DB PREVIEW"
            )

        else:
            blocked += 1
            out()
            out(
                "CONTRACT STATE: BLOCKED BY VALIDATION ERROR"
            )

        out()

    out("=" * 150)
    out("SUMMARY")
    out("=" * 150)

    out(
        "TOTAL CONTRACTS:",
        len(CONTRACTS)
    )

    out(
        "APPROVED FOR COPY-DB PREVIEW:",
        approved
    )

    out(
        "BLOCKED:",
        blocked
    )

    out(
        "ERROR:",
        errors
    )

    out(
        "DATABASE UNCHANGED"
    )

    out("=" * 150)


db.close()

print(
    "TARGET CONTRACT BUILDER TAMAMLANDI"
)

print(
    "FILE:",
    OUT
)

print(
    "TOTAL CONTRACTS:",
    len(CONTRACTS)
)

print(
    "APPROVED FOR COPY-DB PREVIEW:",
    approved
)

print(
    "BLOCKED:",
    blocked
)

print(
    "ERROR:",
    errors
)

print(
    "DATABASE UNCHANGED"
)
