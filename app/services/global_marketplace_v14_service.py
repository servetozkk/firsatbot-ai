from __future__ import annotations

import math
import re
import sqlite3
from pathlib import Path
from typing import Any
from contextlib import closing

DB_PATH = Path("data/products.db")


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _slug(value: str) -> str:
    table = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    value = (value or "urun").translate(table).lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "urun"


def _money(value: Any) -> str:
    try:
        return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " TL"
    except (TypeError, ValueError):
        return "Fiyat yok"


def _stock_label(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if any(x in text for x in ("stokta", "mevcut", "available", "var", "active")):
        return "Stokta"
    if any(x in text for x in ("tükendi", "stokta yok", "out of stock", "inactive")):
        return "Stokta yok"
    return str(value or "Stok bilgisi yok")


def list_global_products(*, q: str = "", brand: str = "", sort: str = "popular", page: int = 1, limit: int = 24) -> dict[str, Any]:
    safe_page = max(1, int(page or 1))
    safe_limit = max(6, min(int(limit or 24), 60))
    where = ["gp.status='ACTIVE'", "oa.offer_count > 0"]
    params: list[Any] = []

    if q.strip():
        needle = f"%{q.strip().casefold()}%"
        where.append("(LOWER(gp.canonical_name) LIKE ? OR LOWER(COALESCE(gp.normalized_brand,'')) LIKE ? OR LOWER(COALESCE(gp.family,'')) LIKE ?)")
        params.extend([needle, needle, needle])
    if brand.strip():
        where.append("LOWER(COALESCE(gp.normalized_brand,''))=?")
        params.append(brand.strip().casefold())

    order_sql = {
        "price_asc": "oa.best_price ASC, gp.canonical_name ASC",
        "price_desc": "oa.best_price DESC, gp.canonical_name ASC",
        "offers": "oa.offer_count DESC, oa.best_price ASC",
        "newest": "gp.updated_at DESC",
        "popular": "oa.offer_count DESC, gp.raw_product_count DESC, oa.best_price ASC",
    }.get(sort, "oa.offer_count DESC, gp.raw_product_count DESC, oa.best_price ASC")

    cte = """
        WITH offer_agg AS (
            SELECT global_product_id,
                   MIN(CASE WHEN current_price > 0 THEN current_price END) AS best_price,
                   MAX(CASE WHEN current_price > 0 THEN current_price END) AS highest_price,
                   COUNT(DISTINCT CASE WHEN current_price > 0 THEN store_code END) AS offer_count
            FROM global_offers
            WHERE is_active=1 AND is_hidden=0 AND lifecycle_status='ACTIVE'
            GROUP BY global_product_id
        ),
        variant_agg AS (
            SELECT global_product_id, COUNT(*) AS variant_count
            FROM global_product_variants
            GROUP BY global_product_id
        )
    """

    with closing(_connect()) as con:
        total = con.execute(cte + f"""
            SELECT COUNT(*) AS c
            FROM global_products gp
            JOIN offer_agg oa ON oa.global_product_id=gp.id
            WHERE {' AND '.join(where)}
        """, params).fetchone()["c"]

        rows = con.execute(cte + f"""
            SELECT gp.id,gp.identity_key,gp.canonical_name,gp.normalized_brand,gp.family,
                   gp.ram_gb,gp.storage_gb,gp.primary_image,gp.updated_at,
                   oa.best_price,oa.highest_price,oa.offer_count,
                   COALESCE(va.variant_count,0) AS variant_count
            FROM global_products gp
            JOIN offer_agg oa ON oa.global_product_id=gp.id
            LEFT JOIN variant_agg va ON va.global_product_id=gp.id
            WHERE {' AND '.join(where)}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
        """, params + [safe_limit, (safe_page - 1) * safe_limit]).fetchall()

        brands = [dict(r) for r in con.execute("""
            SELECT gp.normalized_brand AS brand, COUNT(*) AS product_count
            FROM global_products gp
            JOIN (
                SELECT DISTINCT global_product_id
                FROM global_offers
                WHERE is_active=1 AND is_hidden=0 AND lifecycle_status='ACTIVE' AND current_price>0
            ) active ON active.global_product_id=gp.id
            WHERE gp.status='ACTIVE' AND gp.normalized_brand IS NOT NULL AND gp.normalized_brand<>''
            GROUP BY gp.normalized_brand
            ORDER BY product_count DESC,brand ASC LIMIT 40
        """).fetchall()]

    items = []
    for row in rows:
        item = dict(row)
        item["slug"] = _slug(item["canonical_name"])
        item["best_price_text"] = _money(item["best_price"])
        item["highest_price_text"] = _money(item["highest_price"])
        item["saving_percent"] = round((item["highest_price"] - item["best_price"]) / item["highest_price"] * 100, 2) if item["highest_price"] and item["highest_price"] > item["best_price"] else 0
        items.append(item)

    return {"items": items, "brands": brands, "filters": {"q": q, "brand": brand, "sort": sort}, "pagination": {"page": safe_page, "limit": safe_limit, "total": int(total), "pages": max(1, math.ceil(int(total) / safe_limit))}}


def get_global_product(product_id: int) -> dict[str, Any] | None:
    with closing(_connect()) as con:
        row = con.execute("SELECT * FROM global_products WHERE id=? AND status='ACTIVE'", (int(product_id),)).fetchone()
        if row is None:
            return None
        variants = [dict(r) for r in con.execute("SELECT id,variant_key,color,network,model_code,primary_image FROM global_product_variants WHERE global_product_id=? ORDER BY id", (int(product_id),)).fetchall()]
        offers = [dict(r) for r in con.execute("""
            SELECT go.store_code,go.store_product_id,
                   COALESCE(rp.title_raw,gp.canonical_name) AS title,
                   go.current_price AS price,go.old_price,
                   go.availability AS stock_status,go.seller,
                   go.url AS source_url,
                   COALESCE(rp.image_raw,gp.primary_image) AS image_url,
                   go.updated_at,go.global_variant_id,
                   go.shipping_price,go.delivery_text,go.warranty_type,
                   go.campaign_text,go.installment_text,go.is_official_seller
            FROM global_offers go
            JOIN global_products gp ON gp.id=go.global_product_id
            LEFT JOIN raw_products rp
                   ON rp.id=go.raw_product_id
                  AND rp.global_product_id=go.global_product_id
            WHERE go.global_product_id=? AND go.current_price>0
              AND go.is_active=1 AND go.is_hidden=0 AND go.lifecycle_status='ACTIVE'
            ORDER BY go.current_price ASC,go.updated_at DESC
        """, (int(product_id),)).fetchall()]

    if not offers:
        return None
    product = dict(row)
    product["slug"] = _slug(product["canonical_name"])
    product["variants"] = variants
    if not product.get("primary_image"):
        product["primary_image"] = next((o.get("image_url") for o in offers if o.get("image_url")), None)
    best = min(float(x["price"]) for x in offers)
    highest = max(float(x["price"]) for x in offers)
    seen = set()
    normalized_offers = []
    for offer in offers:
        dedupe = (offer["store_code"], offer["store_product_id"] or offer["source_url"])
        if dedupe in seen:
            continue
        seen.add(dedupe)
        offer["price_text"] = _money(offer["price"])
        offer["old_price_text"] = _money(offer["old_price"]) if offer["old_price"] else None
        offer["stock_label"] = _stock_label(offer["stock_status"])
        offer["is_best"] = float(offer["price"]) == best
        offer["saving_vs_highest"] = round(highest - float(offer["price"]), 2)
        offer["saving_vs_highest_text"] = _money(offer["saving_vs_highest"]) if offer["saving_vs_highest"] > 0 else None
        normalized_offers.append(offer)
    product["offers"] = normalized_offers
    product["offer_count"] = len(normalized_offers)
    product["store_count"] = len({x["store_code"] for x in normalized_offers})
    product["best_price"] = best
    product["best_price_text"] = _money(best)
    product["highest_price"] = highest
    product["highest_price_text"] = _money(highest)
    product["saving_amount"] = round(highest - best, 2)
    product["saving_amount_text"] = _money(product["saving_amount"])
    product["saving_percent"] = round((highest - best) / highest * 100, 2) if highest > best else 0
    product["price_status"] = "En iyi fiyat" if product["saving_percent"] > 0 else "Tek fiyat"
    return product
