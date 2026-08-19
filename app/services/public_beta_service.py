from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.beta_readiness_service import build_beta_readiness

ENGINE_VERSION = "13.9.0"
MODE = "PUBLIC_BETA"
ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "data" / "reports" / "v13_9_0_public_beta.json"
ALLOWED_FEEDBACK_TYPES = {
    "bug", "wrong_price", "wrong_match", "missing_store", "feature_request", "other"
}
ALLOWED_STATUSES = {"new", "reviewing", "resolved", "rejected"}


def _connect() -> sqlite3.Connection:
    path = os.environ.get("FIRSATAI_PUBLIC_BETA_DB_PATH") or str(settings.database_path)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def ensure_schema() -> None:
    with closing(_connect()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS public_beta_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_type TEXT NOT NULL,
                message TEXT NOT NULL,
                page_path TEXT NULL,
                product_key TEXT NULL,
                store_code TEXT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                app_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_public_beta_feedback_status_created
                ON public_beta_feedback(status, created_at DESC);
            CREATE INDEX IF NOT EXISTS ix_public_beta_feedback_type_created
                ON public_beta_feedback(feedback_type, created_at DESC);
            """
        )
        conn.commit()


def _clean(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def submit_feedback(*, feedback_type: str, message: str, page_path: str | None = None,
                    product_key: str | None = None, store_code: str | None = None) -> dict[str, Any]:
    ensure_schema()
    kind = str(feedback_type).strip().lower()
    if kind not in ALLOWED_FEEDBACK_TYPES:
        raise ValueError("Desteklenmeyen geri bildirim türü")
    clean_message = _clean(message, 3000)
    if not clean_message or len(clean_message) < 5:
        raise ValueError("Geri bildirim en az 5 karakter olmalı")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect()) as conn:
        cur = conn.execute(
            """INSERT INTO public_beta_feedback
            (feedback_type,message,page_path,product_key,store_code,status,app_version,created_at,updated_at)
            VALUES (?,?,?,?,?,'new',?,?,?)""",
            (kind, clean_message, _clean(page_path, 400), _clean(product_key, 180),
             _clean(store_code, 100), ENGINE_VERSION, now, now),
        )
        conn.commit()
        return {"id": int(cur.lastrowid), "status": "new", "feedback_type": kind,
                "created_at": now, "anonymous": True}


def list_feedback(*, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    ensure_schema()
    limit = max(1, min(int(limit), 500))
    sql = "SELECT * FROM public_beta_feedback"
    params: list[Any] = []
    if status:
        normalized = str(status).strip().lower()
        if normalized not in ALLOWED_STATUSES:
            raise ValueError("Geçersiz durum")
        sql += " WHERE status=?"
        params.append(normalized)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with closing(_connect()) as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def update_feedback_status(feedback_id: int, status: str) -> dict[str, Any]:
    ensure_schema()
    normalized = str(status).strip().lower()
    if normalized not in ALLOWED_STATUSES:
        raise ValueError("Geçersiz durum")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect()) as conn:
        cur = conn.execute("UPDATE public_beta_feedback SET status=?, updated_at=? WHERE id=?",
                           (normalized, now, int(feedback_id)))
        conn.commit()
        if cur.rowcount == 0:
            raise LookupError("Geri bildirim bulunamadı")
    return {"id": int(feedback_id), "status": normalized, "updated_at": now}


def _table_count(conn: sqlite3.Connection, table: str, where: str = "", params: tuple = ()) -> int:
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not exists:
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} {where}", params).fetchone()[0])


def statistics(days: int = 30) -> dict[str, Any]:
    ensure_schema()
    days = max(1, min(int(days), 365))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    with closing(_connect()) as conn:
        feedback_total = _table_count(conn, "public_beta_feedback", "WHERE created_at>=?", (since,))
        feedback_open = _table_count(conn, "public_beta_feedback", "WHERE status IN ('new','reviewing')")
        analytics_events = _table_count(conn, "anonymous_analytics_events", "WHERE created_at>=?", (since,))
        searches = _table_count(conn, "anonymous_analytics_events", "WHERE created_at>=? AND event_type='search'", (since,))
        active_alerts = _table_count(conn, "advanced_alerts", "WHERE status IN ('ACTIVE','WAITING')")
        feedback_types = {}
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='public_beta_feedback'").fetchone():
            feedback_types = {row[0]: row[1] for row in conn.execute(
                "SELECT feedback_type, COUNT(*) FROM public_beta_feedback WHERE created_at>=? GROUP BY feedback_type", (since,)
            ).fetchall()}
    return {
        "engine_version": ENGINE_VERSION, "mode": MODE, "days": days,
        "feedback_total": feedback_total, "feedback_open": feedback_open,
        "analytics_events": analytics_events, "searches": searches,
        "active_alerts": active_alerts, "feedback_types": feedback_types,
    }


def public_beta_status(write_report: bool = False) -> dict[str, Any]:
    readiness = build_beta_readiness(write_report=False)
    stats = statistics(30)
    maintenance = os.environ.get("FIRSATAI_MAINTENANCE_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}
    blockers = list(readiness.get("blockers") or [])
    status = "PUBLIC_BETA_READY" if readiness.get("status") == "BETA_READY" and not blockers else "PUBLIC_BETA_BLOCKED"
    payload = {
        "engine_version": ENGINE_VERSION,
        "mode": MODE,
        "status": status,
        "maintenance_mode": maintenance,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "beta_readiness": readiness.get("status"),
        "module_summary": readiness.get("summary", {}),
        "source_metrics": readiness.get("source_metrics", {}),
        "database": readiness.get("database", {}),
        "statistics": stats,
        "feedback_enabled": True,
        "blockers": blockers,
    }
    if write_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
