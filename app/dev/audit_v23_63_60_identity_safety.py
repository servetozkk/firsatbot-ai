
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "products.db"

db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True,
)

checks = {
    "history_wrong_gp": """
        SELECT COUNT(*)
        FROM global_offer_price_history h
        JOIN global_product_variants gv ON gv.id=h.global_variant_id
        WHERE h.global_variant_id IS NOT NULL
          AND h.global_product_id != gv.global_product_id
    """,
    "variant_drift": """
        SELECT COUNT(*)
        FROM global_offers go
        JOIN raw_products rp ON rp.id=go.raw_product_id
        WHERE go.is_active=1
          AND go.global_variant_id IS NOT NULL
          AND rp.global_variant_id IS NOT NULL
          AND go.global_variant_id != rp.global_variant_id
    """,
    "offer_variant_wrong_gp": """
        SELECT COUNT(*)
        FROM global_offers go
        JOIN global_product_variants gv ON gv.id=go.global_variant_id
        WHERE go.global_variant_id IS NOT NULL
          AND go.global_product_id != gv.global_product_id
    """,
    "raw_variant_wrong_gp": """
        SELECT COUNT(*)
        FROM raw_products rp
        JOIN global_product_variants gv ON gv.id=rp.global_variant_id
        WHERE rp.global_variant_id IS NOT NULL
          AND rp.global_product_id != gv.global_product_id
    """,
    "raw_counter": """
        SELECT COUNT(*)
        FROM global_products gp
        WHERE gp.raw_product_count != (
            SELECT COUNT(*) FROM raw_products rp
            WHERE rp.global_product_id=gp.id
        )
    """,
    "offer_counter": """
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
    """,
    "quarantine": """
        SELECT COUNT(*)
        FROM global_offers
        WHERE lifecycle_status='QUARANTINED'
          AND (is_active=1 OR is_hidden=0)
    """,
    "duplicate_variant_keys": """
        SELECT COUNT(*)
        FROM (
            SELECT global_product_id,variant_key,COUNT(*) c
            FROM global_product_variants
            GROUP BY global_product_id,variant_key
            HAVING COUNT(*)>1
        )
    """,
}

result = {name: db.execute(sql).fetchone()[0] for name, sql in checks.items()}
db.close()

if any(result.values()):
    raise RuntimeError("V23.63.60 read-only baseline failure: {}".format(result))

print("V23.63.60 READ-ONLY identity safety audit OK:", result)
