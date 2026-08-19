from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService
from app.services.bulk_catalog_service import init_bulk_catalog_schema

DB_PATH = Path("data/products.db")
_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_model_code(value: Any) -> str | None:
    text = " ".join(str(value or "").split()).strip()
    if not text or ProductIdentityService._is_pseudo_model_code(text):
        return None
    return text


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def init_bulk_identity_schema() -> None:
    init_bulk_catalog_schema()
    with _LOCK, _connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS bulk_identity_links (
                item_id INTEGER PRIMARY KEY,
                global_product_id INTEGER NOT NULL,
                global_variant_id INTEGER,
                identity_key TEXT NOT NULL,
                identity_source TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 100,
                decision TEXT NOT NULL,
                linked_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(item_id) REFERENCES bulk_catalog_items(id) ON DELETE CASCADE,
                FOREIGN KEY(global_product_id) REFERENCES global_products(id) ON DELETE CASCADE,
                FOREIGN KEY(global_variant_id) REFERENCES global_product_variants(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS ix_bulk_identity_global
            ON bulk_identity_links(global_product_id, updated_at);

            CREATE TABLE IF NOT EXISTS bulk_identity_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                identity_key TEXT,
                candidate_global_product_id INTEGER,
                decision TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0,
                reasons_json TEXT,
                conflicts_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(item_id) REFERENCES bulk_catalog_items(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS ix_bulk_decisions_item
            ON bulk_identity_decisions(item_id, created_at);
            """
        )
        con.commit()


def _product_from_row(row: sqlite3.Row) -> Product:
    return Product(
        name=str(row["title"] or ""),
        price=float(row["price"] or 0),
        old_price=float(row["old_price"]) if row["old_price"] is not None else None,
        rating=None,
        review_count=None,
        seller=str(row["seller"] or row["store_code"] or ""),
        url=str(row["source_url"] or ""),
        image=str(row["image_url"] or "") or None,
        brand=str(row["brand"] or "") or None,
        model=None,
        category=None,
        description=None,
        specifications=None,
        stock_status=str(row["stock_status"] or "") or None,
        source_site=str(row["store_code"] or ""),
        product_code=str(row["store_product_id"] or "") or None,
    )


def _variant_key(explain: dict[str, Any]) -> str:
    parsed = explain["parsed"]
    parts = []
    for key in ("color", "network", "model_code"):
        if key == "model_code":
            value = _safe_model_code(parsed.get(key)) or ""
        else:
            value = str(parsed.get(key) or "").strip()
        if value:
            parts.append(f"{key}={value}")
    return "|".join(parts) or "default"


def _canonical_name(product: Product, explain: dict[str, Any]) -> str:
    parsed = explain["parsed"]
    pieces = [str(product.brand or parsed.get("brand") or "").strip(), str(parsed.get("family") or "").strip()]
    if parsed.get("variant"):
        pieces.append(str(parsed["variant"]).strip())
    if parsed.get("ram_gb") is not None:
        pieces.append(f"{parsed['ram_gb']} GB RAM")
    if parsed.get("storage_gb") is not None:
        pieces.append(f"{parsed['storage_gb']} GB")
    value = " ".join(x for x in pieces if x).strip()
    return value or str(product.name or "Ürün").strip()


def _upsert_global(con: sqlite3.Connection, product: Product, explain: dict[str, Any]) -> tuple[int, str]:
    now = _now()
    key = explain["identity_key"]
    parsed = explain["parsed"]
    existing = con.execute("SELECT id FROM global_products WHERE identity_key=?", (key,)).fetchone()
    values = (
        explain["identity_source"], _canonical_name(product, explain),
        explain["normalized_brand"] or None, parsed.get("family") or None,
        parsed.get("normalized_model") or explain.get("normalized_model") or None,
        parsed.get("variant") or None, parsed.get("ram_gb"), parsed.get("storage_gb"),
        parsed.get("screen_inch"), _safe_model_code(parsed.get("model_code")),
        product.category, product.image, now,
    )
    if existing:
        gid = int(existing["id"])
        con.execute(
            """UPDATE global_products SET identity_source=?,canonical_name=?,normalized_brand=?,family=?,model=?,variant=?,
            ram_gb=?,storage_gb=?,screen_inch=?,model_code=?,category=COALESCE(?,category),primary_image=COALESCE(?,primary_image),
            raw_product_count=(SELECT COUNT(*) FROM raw_products WHERE global_product_id=?),updated_at=? WHERE id=?""",
            values[:-1] + (gid, now, gid),
        )
        action = "matched"
    else:
        cur = con.execute(
            """INSERT INTO global_products(identity_key,identity_source,canonical_name,normalized_brand,family,model,variant,
            ram_gb,storage_gb,screen_inch,model_code,category,primary_image,raw_product_count,active_offer_count,status,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,'ACTIVE',?,?)""",
            (key,) + values[:-1] + (now, now),
        )
        gid = int(cur.lastrowid)
        action = "created"
    return gid, action


def _upsert_variant(con: sqlite3.Connection, global_id: int, product: Product, explain: dict[str, Any]) -> int:
    now = _now()
    parsed = explain["parsed"]
    key = _variant_key(explain)
    existing = con.execute(
        "SELECT id FROM global_product_variants WHERE global_product_id=? AND variant_key=?",
        (global_id, key),
    ).fetchone()
    if existing:
        vid = int(existing["id"])
        con.execute(
            """UPDATE global_product_variants SET color=?,network=?,model_code=?,primary_image=COALESCE(?,primary_image),updated_at=? WHERE id=?""",
            (parsed.get("color") or None, parsed.get("network") or None, _safe_model_code(parsed.get("model_code")), product.image, now, vid),
        )
        return vid
    cur = con.execute(
        """INSERT INTO global_product_variants(global_product_id,variant_key,color,network,model_code,primary_image,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?)""",
        (global_id, key, parsed.get("color") or None, parsed.get("network") or None, _safe_model_code(parsed.get("model_code")), product.image, now, now),
    )
    return int(cur.lastrowid)


@dataclass(slots=True)
class BatchResult:
    processed: int = 0
    created_products: int = 0
    matched_products: int = 0
    failed: int = 0
    remaining: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def process_match_queue(limit: int = 250) -> dict[str, Any]:
    """Staging kuyruğunu toplu biçimde global ürünlere bağlar.

    Ingestion sırasında hiçbir mağazada çapraz arama yapmaz. Aynı identity_key
    aynı global ürüne, renk/ağ/model kodu ise alt varyanta bağlanır.
    """
    init_bulk_identity_schema()
    result = BatchResult()
    with _LOCK, _connect() as con:
        rows = con.execute(
            """SELECT q.id queue_id,q.attempts,i.* FROM bulk_match_queue q
            JOIN bulk_catalog_items i ON i.id=q.item_id
            WHERE q.status IN ('PENDING','RETRY') AND q.available_at<=?
            ORDER BY q.priority ASC,q.id ASC LIMIT ?""",
            (_now(), max(1, min(int(limit), 2000))),
        ).fetchall()

        for row in rows:
            qid, item_id = int(row["queue_id"]), int(row["id"])
            con.execute("UPDATE bulk_match_queue SET status='PROCESSING',locked_at=?,updated_at=? WHERE id=?", (_now(), _now(), qid))
            try:
                product = _product_from_row(row)
                ProductIdentityService.enrich_product(product)
                explain = ProductIdentityService.explain(product)
                if not explain.get("normalized_brand") or not explain["parsed"].get("family"):
                    raise ValueError("Marka veya ürün ailesi çıkarılamadı")
                gid, action = _upsert_global(con, product, explain)
                vid = _upsert_variant(con, gid, product, explain)
                now = _now()
                con.execute(
                    """INSERT INTO bulk_identity_links(item_id,global_product_id,global_variant_id,identity_key,identity_source,confidence,decision,linked_at,updated_at)
                    VALUES(?,?,?,?,?,100,?,?,?)
                    ON CONFLICT(item_id) DO UPDATE SET global_product_id=excluded.global_product_id,
                    global_variant_id=excluded.global_variant_id,identity_key=excluded.identity_key,identity_source=excluded.identity_source,
                    confidence=excluded.confidence,decision=excluded.decision,updated_at=excluded.updated_at""",
                    (item_id, gid, vid, explain["identity_key"], explain["identity_source"], "AUTO_MATCH" if action == "matched" else "CREATE_NEW", now, now),
                )
                con.execute(
                    """INSERT INTO bulk_identity_decisions(item_id,identity_key,candidate_global_product_id,decision,confidence,reasons_json,conflicts_json,created_at)
                    VALUES(?,?,?,?,100,?,?,?)""",
                    (item_id, explain["identity_key"], gid, "AUTO_MATCH" if action == "matched" else "CREATE_NEW", json.dumps(["Identity key deterministik eşleşti"], ensure_ascii=False), "[]", now),
                )
                con.execute("UPDATE bulk_catalog_items SET match_status='MATCHED',updated_at=? WHERE id=?", (now, item_id))
                con.execute("UPDATE bulk_match_queue SET status='DONE',finished_at=?,last_error=NULL,updated_at=? WHERE id=?", (now, now, qid))
                result.processed += 1
                if action == "created": result.created_products += 1
                else: result.matched_products += 1
            except Exception as exc:  # noqa: BLE001
                now = _now()
                attempts = int(row["attempts"] or 0) + 1
                status = "RETRY" if attempts < 3 else "FAILED"
                con.execute("UPDATE bulk_match_queue SET status=?,attempts=?,last_error=?,locked_at=NULL,updated_at=? WHERE id=?", (status, attempts, f"{type(exc).__name__}: {exc}", now, qid))
                con.execute("UPDATE bulk_catalog_items SET match_status=?,updated_at=? WHERE id=?", (status, now, item_id))
                result.failed += 1
            con.commit()

        result.remaining = int(con.execute("SELECT COUNT(*) c FROM bulk_match_queue WHERE status IN ('PENDING','RETRY')").fetchone()["c"])
    return result.to_dict()


def identity_status() -> dict[str, Any]:
    init_bulk_identity_schema()
    with _connect() as con:
        counts = {
            "staged": con.execute("SELECT COUNT(*) c FROM bulk_catalog_items").fetchone()["c"],
            "pending": con.execute("SELECT COUNT(*) c FROM bulk_match_queue WHERE status IN ('PENDING','RETRY')").fetchone()["c"],
            "matched": con.execute("SELECT COUNT(*) c FROM bulk_identity_links").fetchone()["c"],
            "global_products": con.execute("SELECT COUNT(*) c FROM global_products").fetchone()["c"],
            "variants": con.execute("SELECT COUNT(*) c FROM global_product_variants").fetchone()["c"],
            "failed": con.execute("SELECT COUNT(*) c FROM bulk_match_queue WHERE status='FAILED'").fetchone()["c"],
        }
        recent = [dict(r) for r in con.execute(
            """SELECT l.item_id,l.global_product_id,l.identity_source,l.decision,l.updated_at,i.store_code,i.title
            FROM bulk_identity_links l JOIN bulk_catalog_items i ON i.id=l.item_id
            ORDER BY l.updated_at DESC LIMIT 50"""
        ).fetchall()]
    return {"engine_version":"14.3.0","mode":"BULK_IDENTITY","counts":{k:int(v) for k,v in counts.items()},"recent":recent}
