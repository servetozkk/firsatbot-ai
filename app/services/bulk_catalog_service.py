from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from app.category_scrapers.registry import CategoryScraperRegistry
from app.services.catalog_scan_plan_service import get_catalog_plan

DB_PATH = Path("data/products.db")
_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def init_bulk_catalog_schema() -> None:
    with _LOCK, _connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS bulk_catalog_jobs (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                plan_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED',
                current_store TEXT,
                progress INTEGER NOT NULL DEFAULT 0,
                discovered_count INTEGER NOT NULL DEFAULT 0,
                inserted_count INTEGER NOT NULL DEFAULT 0,
                updated_count INTEGER NOT NULL DEFAULT 0,
                unchanged_count INTEGER NOT NULL DEFAULT 0,
                queued_match_count INTEGER NOT NULL DEFAULT 0,
                failed_store_count INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                error TEXT,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bulk_catalog_checkpoints (
                plan_id TEXT NOT NULL,
                store_code TEXT NOT NULL,
                category_url TEXT NOT NULL,
                last_page INTEGER NOT NULL DEFAULT 0,
                last_product_count INTEGER NOT NULL DEFAULT 0,
                last_status TEXT NOT NULL DEFAULT 'NEW',
                last_error TEXT,
                last_run_at TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(plan_id, store_code, category_url)
            );

            CREATE TABLE IF NOT EXISTS bulk_catalog_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_code TEXT NOT NULL,
                store_product_id TEXT,
                source_url TEXT NOT NULL,
                category_url TEXT NOT NULL,
                page_number INTEGER NOT NULL DEFAULT 1,
                title TEXT,
                brand TEXT,
                seller TEXT,
                price REAL,
                old_price REAL,
                stock_status TEXT,
                image_url TEXT,
                payload_hash TEXT NOT NULL,
                detail_status TEXT NOT NULL DEFAULT 'PENDING',
                match_status TEXT NOT NULL DEFAULT 'PENDING',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(store_code, source_url)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS uq_bulk_store_product
            ON bulk_catalog_items(store_code, store_product_id)
            WHERE store_product_id IS NOT NULL AND store_product_id <> '';

            CREATE INDEX IF NOT EXISTS ix_bulk_items_match_status
            ON bulk_catalog_items(match_status, updated_at);

            CREATE TABLE IF NOT EXISTS bulk_match_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'PENDING',
                priority INTEGER NOT NULL DEFAULT 100,
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at TEXT NOT NULL,
                locked_at TEXT,
                finished_at TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(item_id) REFERENCES bulk_catalog_items(id) ON DELETE CASCADE
            );
            """
        )
        con.commit()


def _fingerprint(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def stage_item(*, store_code: str, category_url: str, item: Any) -> dict[str, Any]:
    """Kategori kartını staging alanına idempotent biçimde yazar.

    Aynı mağaza ürünü tekrar geldiğinde INSERT yerine UPDATE yapılır. İçerik
    değişmediyse eşleştirme kuyruğu gereksiz yere büyütülmez.
    """
    init_bulk_catalog_schema()
    now = _now()
    payload = {
        "store_code": str(store_code or "").strip().casefold(),
        "store_product_id": str(getattr(item, "product_code", "") or "").strip() or None,
        "source_url": str(getattr(item, "url", "") or "").strip(),
        "category_url": str(category_url or "").strip(),
        "page_number": max(1, int(getattr(item, "page_number", 1) or 1)),
        "title": str(getattr(item, "name", "") or "").strip() or None,
        "brand": str(getattr(item, "brand", "") or "").strip() or None,
        "seller": str(getattr(item, "seller", "") or "").strip() or None,
        "price": getattr(item, "price", None),
        "old_price": getattr(item, "old_price", None),
        "stock_status": str(getattr(item, "stock_status", "") or "").strip() or None,
        "image_url": str(getattr(item, "image", "") or "").strip() or None,
    }
    if not payload["store_code"] or not payload["source_url"]:
        raise ValueError("Staging için mağaza kodu ve ürün URL'si zorunludur.")
    content_hash = _fingerprint(payload)

    with _LOCK, _connect() as con:
        existing = None
        if payload["store_product_id"]:
            existing = con.execute(
                "SELECT * FROM bulk_catalog_items WHERE store_code=? AND store_product_id=?",
                (payload["store_code"], payload["store_product_id"]),
            ).fetchone()
        if existing is None:
            existing = con.execute(
                "SELECT * FROM bulk_catalog_items WHERE store_code=? AND source_url=?",
                (payload["store_code"], payload["source_url"]),
            ).fetchone()

        changed = existing is None or existing["payload_hash"] != content_hash
        if existing is None:
            cur = con.execute(
                """INSERT INTO bulk_catalog_items(
                    store_code,store_product_id,source_url,category_url,page_number,
                    title,brand,seller,price,old_price,stock_status,image_url,payload_hash,
                    detail_status,match_status,first_seen_at,last_seen_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'PENDING','PENDING',?,?,?)""",
                (
                    payload["store_code"], payload["store_product_id"], payload["source_url"],
                    payload["category_url"], payload["page_number"], payload["title"],
                    payload["brand"], payload["seller"], payload["price"], payload["old_price"],
                    payload["stock_status"], payload["image_url"], content_hash, now, now, now,
                ),
            )
            item_id = int(cur.lastrowid)
            action = "inserted"
        else:
            item_id = int(existing["id"])
            con.execute(
                """UPDATE bulk_catalog_items SET
                    store_product_id=COALESCE(?,store_product_id),source_url=?,category_url=?,page_number=?,
                    title=?,brand=?,seller=?,price=?,old_price=?,stock_status=?,image_url=?,payload_hash=?,
                    detail_status=CASE WHEN ? THEN 'PENDING' ELSE detail_status END,
                    match_status=CASE WHEN ? THEN 'PENDING' ELSE match_status END,
                    last_seen_at=?,updated_at=? WHERE id=?""",
                (
                    payload["store_product_id"], payload["source_url"], payload["category_url"],
                    payload["page_number"], payload["title"], payload["brand"], payload["seller"],
                    payload["price"], payload["old_price"], payload["stock_status"], payload["image_url"],
                    content_hash, int(changed), int(changed), now, now, item_id,
                ),
            )
            action = "updated" if changed else "unchanged"

        queued = False
        if changed:
            con.execute(
                """INSERT INTO bulk_match_queue(item_id,status,priority,attempts,available_at,created_at,updated_at)
                VALUES(?,'PENDING',100,0,?,?,?)
                ON CONFLICT(item_id) DO UPDATE SET status='PENDING',available_at=excluded.available_at,
                    locked_at=NULL,finished_at=NULL,last_error=NULL,updated_at=excluded.updated_at""",
                (item_id, now, now, now),
            )
            queued = True
        con.commit()
    return {"item_id": item_id, "action": action, "queued": queued}


def _checkpoint(plan_id: str, store_code: str, category_url: str, *, page: int, count: int, status: str, error: str | None = None) -> None:
    now = _now()
    with _LOCK, _connect() as con:
        con.execute(
            """INSERT INTO bulk_catalog_checkpoints(plan_id,store_code,category_url,last_page,last_product_count,last_status,last_error,last_run_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(plan_id,store_code,category_url) DO UPDATE SET
                last_page=excluded.last_page,last_product_count=excluded.last_product_count,
                last_status=excluded.last_status,last_error=excluded.last_error,
                last_run_at=excluded.last_run_at,updated_at=excluded.updated_at""",
            (plan_id, store_code, category_url, page, count, status, error, now, now),
        )
        con.commit()


@dataclass(slots=True)
class BulkRunResult:
    plan_id: str
    plan_name: str
    discovered_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    queued_match_count: int = 0
    failed_store_count: int = 0
    stores: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_bulk_plan(plan_id: str, progress: Callable[[int, str, str], None] | None = None) -> BulkRunResult:
    """Mağaza kataloglarını bağımsız biçimde staging alanına toplar.

    Bu fonksiyon bilinçli olarak CrossStoreSearchService çağırmaz. Mağazalar
    tarama sırasında birbirinde aranmaz; eşleştirme bulk_match_queue üzerinden
    daha sonra toplu worker tarafından yapılır.
    """
    init_bulk_catalog_schema()
    plan = get_catalog_plan(plan_id)
    if not plan:
        raise ValueError("Katalog planı bulunamadı.")
    sources = [s for s in plan["sources"] if s.get("active", True)]
    result = BulkRunResult(plan_id=plan["id"], plan_name=plan["name"])
    registry = CategoryScraperRegistry()

    for index, source in enumerate(sources, 1):
        store_code = source["store_code"]
        store_name = source["store_name"]
        category_url = source["url"]
        if progress:
            progress(int((index - 1) / max(1, len(sources)) * 100), store_code, f"{store_name} kategori sayfaları toplu taranıyor")
        try:
            scraper = registry.get_scraper(category_url)
            collected = scraper.collect_product_links(
                category_url=category_url,
                limit=int(plan.get("limit", 100)),
                max_pages=100,
            )
            counters = {"inserted": 0, "updated": 0, "unchanged": 0, "queued": 0}
            for pos, link in enumerate(collected.links, 1):
                staged = stage_item(store_code=store_code, category_url=category_url, item=link)
                counters[staged["action"]] += 1
                counters["queued"] += int(staged["queued"])
                if progress and (pos == len(collected.links) or pos % 25 == 0):
                    local = pos / max(1, len(collected.links))
                    overall = int(((index - 1 + local) / max(1, len(sources))) * 100)
                    progress(min(99, overall), store_code, f"{store_name}: {pos}/{len(collected.links)} ürün staging alanına yazıldı")
            result.discovered_count += len(collected.links)
            result.inserted_count += counters["inserted"]
            result.updated_count += counters["updated"]
            result.unchanged_count += counters["unchanged"]
            result.queued_match_count += counters["queued"]
            _checkpoint(plan["id"], store_code, category_url, page=collected.visited_page_count, count=len(collected.links), status="COMPLETED")
            result.stores.append({
                "store_code": store_code, "store_name": store_name, "success": True,
                "visited_pages": collected.visited_page_count, "discovered": len(collected.links), **counters,
            })
        except Exception as exc:  # noqa: BLE001
            result.failed_store_count += 1
            _checkpoint(plan["id"], store_code, category_url, page=0, count=0, status="FAILED", error=f"{type(exc).__name__}: {exc}")
            result.stores.append({"store_code": store_code, "store_name": store_name, "success": False, "error": f"{type(exc).__name__}: {exc}"})
    if progress:
        progress(100, "", "Toplu katalog toplama tamamlandı; değişen ürünler eşleştirme kuyruğuna alındı")
    return result


def catalog_status() -> dict[str, Any]:
    init_bulk_catalog_schema()
    with _connect() as con:
        items = con.execute("SELECT COUNT(*) c FROM bulk_catalog_items").fetchone()["c"]
        pending = con.execute("SELECT COUNT(*) c FROM bulk_match_queue WHERE status='PENDING'").fetchone()["c"]
        stores = con.execute("SELECT store_code,COUNT(*) c FROM bulk_catalog_items GROUP BY store_code ORDER BY c DESC").fetchall()
        checkpoints = con.execute("SELECT * FROM bulk_catalog_checkpoints ORDER BY updated_at DESC LIMIT 50").fetchall()
    return {
        "engine_version": "14.2.0",
        "mode": "BULK_CATALOG",
        "staged_item_count": int(items),
        "pending_match_count": int(pending),
        "stores": [dict(x) for x in stores],
        "checkpoints": [dict(x) for x in checkpoints],
        "cross_store_search_during_ingestion": False,
    }
