from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings

ENGINE_VERSION = "13.8.2"
ALLOWED_EVENT_TYPES = {
    "page_view", "search", "search_no_results", "product_view",
    "compare_add", "favorite_add", "alert_create", "store_click",
    "filter_use", "sort_use",
}
FORBIDDEN_KEYS = {
    "ip", "ip_address", "email", "e_mail", "username", "user_name",
    "name", "full_name", "phone", "telephone", "owner_key", "user_id",
    "session", "session_id", "visitor_id", "cookie",
}


def _connect() -> sqlite3.Connection:
    db_path = os.environ.get("FIRSATAI_ANALYTICS_DB_PATH") or str(settings.database_path)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def ensure_schema() -> None:
    with closing(_connect()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS anonymous_analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                page_path TEXT NULL,
                search_query TEXT NULL,
                result_count INTEGER NULL,
                product_key TEXT NULL,
                category TEXT NULL,
                brand TEXT NULL,
                store_code TEXT NULL,
                filter_name TEXT NULL,
                sort_name TEXT NULL,
                duration_ms INTEGER NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_analytics_event_time
                ON anonymous_analytics_events(event_type, created_at DESC);
            CREATE INDEX IF NOT EXISTS ix_analytics_search_time
                ON anonymous_analytics_events(search_query, created_at DESC);
            CREATE INDEX IF NOT EXISTS ix_analytics_product_time
                ON anonymous_analytics_events(product_key, created_at DESC);
            CREATE INDEX IF NOT EXISTS ix_analytics_store_time
                ON anonymous_analytics_events(store_code, created_at DESC);
            """
        )
        conn.commit()


def _clean_text(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_length]


def _sanitize_metadata(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return None
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).strip().lower()
            if key_text in FORBIDDEN_KEYS:
                continue
            sanitized = _sanitize_metadata(item, depth + 1)
            if sanitized is not None:
                clean[str(key)[:64]] = sanitized
        return clean
    if isinstance(value, list):
        return [_sanitize_metadata(item, depth + 1) for item in value[:20]]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(value)[:250]


def record_event(
    *,
    event_type: str,
    page_path: str | None = None,
    search_query: str | None = None,
    result_count: int | None = None,
    product_key: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    store_code: str | None = None,
    filter_name: str | None = None,
    sort_name: str | None = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_schema()
    event_type = str(event_type).strip().lower()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError("Desteklenmeyen analitik olay türü")
    safe_metadata = _sanitize_metadata(metadata or {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    duration = None if duration_ms is None else max(0, min(int(duration_ms), 3_600_000))
    count = None if result_count is None else max(0, min(int(result_count), 10_000_000))
    values = (
        event_type,
        _clean_text(page_path, 300),
        _clean_text(search_query, 200),
        count,
        _clean_text(product_key, 160),
        _clean_text(category, 100),
        _clean_text(brand, 100),
        _clean_text(store_code, 100),
        _clean_text(filter_name, 100),
        _clean_text(sort_name, 100),
        duration,
        json.dumps(safe_metadata, ensure_ascii=False, separators=(",", ":")),
        now,
    )
    with closing(_connect()) as conn:
        cur = conn.execute(
            """INSERT INTO anonymous_analytics_events
            (event_type,page_path,search_query,result_count,product_key,category,brand,
             store_code,filter_name,sort_name,duration_ms,metadata_json,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            values,
        )
        conn.commit()
        return {"id": int(cur.lastrowid), "event_type": event_type, "created_at": now, "anonymous": True}


def _since(days: int) -> str:
    days = max(1, min(int(days), 365))
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


def dashboard(days: int = 30) -> dict[str, Any]:
    ensure_schema()
    since = _since(days)
    with closing(_connect()) as conn:
        total = conn.execute("SELECT COUNT(*) FROM anonymous_analytics_events WHERE created_at>=?", (since,)).fetchone()[0]
        searches = conn.execute("SELECT COUNT(*) FROM anonymous_analytics_events WHERE created_at>=? AND event_type='search'", (since,)).fetchone()[0]
        no_results = conn.execute("SELECT COUNT(*) FROM anonymous_analytics_events WHERE created_at>=? AND event_type='search_no_results'", (since,)).fetchone()[0]
        avg_search_ms = conn.execute("SELECT ROUND(AVG(duration_ms),2) FROM anonymous_analytics_events WHERE created_at>=? AND event_type='search' AND duration_ms IS NOT NULL", (since,)).fetchone()[0]
        top_products = [dict(r) for r in conn.execute(
            """SELECT product_key, COUNT(*) AS views FROM anonymous_analytics_events
               WHERE created_at>=? AND event_type='product_view' AND product_key IS NOT NULL
               GROUP BY product_key ORDER BY views DESC, product_key LIMIT 10""", (since,)).fetchall()]
        top_stores = [dict(r) for r in conn.execute(
            """SELECT store_code, COUNT(*) AS clicks FROM anonymous_analytics_events
               WHERE created_at>=? AND event_type='store_click' AND store_code IS NOT NULL
               GROUP BY store_code ORDER BY clicks DESC, store_code LIMIT 10""", (since,)).fetchall()]
        top_searches = [dict(r) for r in conn.execute(
            """SELECT search_query, COUNT(*) AS searches FROM anonymous_analytics_events
               WHERE created_at>=? AND event_type='search' AND search_query IS NOT NULL
               GROUP BY search_query ORDER BY searches DESC, search_query LIMIT 10""", (since,)).fetchall()]
        no_result_queries = [dict(r) for r in conn.execute(
            """SELECT search_query, COUNT(*) AS searches FROM anonymous_analytics_events
               WHERE created_at>=? AND event_type='search_no_results' AND search_query IS NOT NULL
               GROUP BY search_query ORDER BY searches DESC, search_query LIMIT 10""", (since,)).fetchall()]
        event_counts = {r[0]: r[1] for r in conn.execute(
            "SELECT event_type, COUNT(*) FROM anonymous_analytics_events WHERE created_at>=? GROUP BY event_type", (since,)).fetchall()}
    return {
        "engine_version": ENGINE_VERSION,
        "days": max(1, min(int(days), 365)),
        "total_events": total,
        "searches": searches,
        "no_result_searches": no_results,
        "average_search_duration_ms": avg_search_ms or 0,
        "event_counts": event_counts,
        "top_products": top_products,
        "top_stores": top_stores,
        "top_searches": top_searches,
        "no_result_queries": no_result_queries,
        "privacy": {
            "anonymous": True,
            "stores_ip": False,
            "stores_email": False,
            "stores_username": False,
            "requires_cookie_id": False,
        },
    }


def search_metrics(days: int = 30) -> dict[str, Any]:
    data = dashboard(days)
    return {k: data[k] for k in ("engine_version", "days", "searches", "no_result_searches", "average_search_duration_ms", "top_searches", "no_result_queries", "privacy")}


def product_metrics(days: int = 30) -> dict[str, Any]:
    data = dashboard(days)
    return {"engine_version": ENGINE_VERSION, "days": data["days"], "items": data["top_products"], "privacy": data["privacy"]}


def store_metrics(days: int = 30) -> dict[str, Any]:
    data = dashboard(days)
    return {"engine_version": ENGINE_VERSION, "days": data["days"], "items": data["top_stores"], "privacy": data["privacy"]}
