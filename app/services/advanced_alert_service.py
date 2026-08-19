from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any

from app.core.config import settings

ENGINE_VERSION = "13.8.1"
ALERT_TYPES = {
    "price_target", "discount_percent", "stock_back", "coupon_available",
    "campaign_available", "new_seller", "official_seller", "value_score",
}
STATUSES = {"ACTIVE", "WAITING", "TRIGGERED", "DISABLED", "READY_FOR_NOTIFICATION"}


def _connect() -> sqlite3.Connection:
    db_path = os.environ.get("FIRSATAI_ALERT_DB_PATH") or str(settings.database_path)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def ensure_schema() -> None:
    with closing(_connect()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS advanced_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_key TEXT NOT NULL,
                global_product_id INTEGER NULL,
                identity_key TEXT NULL,
                alert_type TEXT NOT NULL,
                threshold_value REAL NULL,
                rule_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                is_active INTEGER NOT NULL DEFAULT 1,
                last_checked_at TEXT NULL,
                last_triggered_at TEXT NULL,
                trigger_count INTEGER NOT NULL DEFAULT 0,
                last_reason TEXT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(global_product_id) REFERENCES global_products(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS ix_advanced_alert_owner_status
                ON advanced_alerts(owner_key, status, is_active);
            CREATE INDEX IF NOT EXISTS ix_advanced_alert_product_type
                ON advanced_alerts(global_product_id, alert_type, is_active);
            CREATE TABLE IF NOT EXISTS advanced_alert_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                reason TEXT NULL,
                previous_value REAL NULL,
                current_value REAL NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(alert_id) REFERENCES advanced_alerts(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS ix_advanced_alert_event_alert_time
                ON advanced_alert_events(alert_id, created_at DESC);
            """
        )
        conn.commit()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in ("rule_json", "payload_json"):
        if key in result:
            try: result[key[:-5] if key.endswith("_json") else key] = json.loads(result[key] or "{}")
            except Exception: result[key[:-5]] = {}
    result["is_active"] = bool(result.get("is_active", 0))
    return result


def create_alert(*, owner_key: str, alert_type: str, global_product_id: int | None = None,
                 identity_key: str | None = None, threshold_value: float | None = None,
                 rule: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_schema()
    if alert_type not in ALERT_TYPES:
        raise ValueError("Desteklenmeyen alarm türü")
    if alert_type in {"price_target", "discount_percent", "value_score"} and threshold_value is None:
        raise ValueError("Bu alarm türü için eşik değeri zorunludur")
    now = datetime.utcnow().isoformat(timespec="seconds")
    with closing(_connect()) as conn:
        cur = conn.execute(
            """INSERT INTO advanced_alerts
            (owner_key, global_product_id, identity_key, alert_type, threshold_value,
             rule_json, status, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', 1, ?, ?)""",
            (owner_key, global_product_id, identity_key, alert_type, threshold_value,
             json.dumps(rule or {}, ensure_ascii=False), now, now),
        )
        alert_id = int(cur.lastrowid)
        conn.execute("INSERT INTO advanced_alert_events(alert_id,event_type,reason,payload_json,created_at) VALUES(?,?,?,?,?)",
                     (alert_id, "CREATED", "Alarm oluşturuldu", "{}", now))
        conn.commit()
        return get_alert(owner_key=owner_key, alert_id=alert_id) or {}


def list_alerts(*, owner_key: str, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    ensure_schema(); limit=max(1,min(int(limit),200))
    sql="SELECT * FROM advanced_alerts WHERE owner_key=?"; params:[Any]=[owner_key]
    if status:
        sql += " AND status=?"; params.append(status.upper())
    sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"; params.append(limit)
    with closing(_connect()) as conn:
        return [_row(r) for r in conn.execute(sql, params).fetchall()]


def get_alert(*, owner_key: str, alert_id: int) -> dict[str, Any] | None:
    ensure_schema()
    with closing(_connect()) as conn:
        return _row(conn.execute("SELECT * FROM advanced_alerts WHERE id=? AND owner_key=?", (alert_id, owner_key)).fetchone())


def update_alert(*, owner_key: str, alert_id: int, threshold_value: float | None = None,
                 rule: dict[str, Any] | None = None, is_active: bool | None = None) -> dict[str, Any] | None:
    alert=get_alert(owner_key=owner_key, alert_id=alert_id)
    if not alert: return None
    threshold = alert.get("threshold_value") if threshold_value is None else threshold_value
    next_rule = alert.get("rule", {}) if rule is None else rule
    active = alert.get("is_active") if is_active is None else bool(is_active)
    status = "ACTIVE" if active else "DISABLED"
    now=datetime.utcnow().isoformat(timespec="seconds")
    with closing(_connect()) as conn:
        conn.execute("UPDATE advanced_alerts SET threshold_value=?, rule_json=?, is_active=?, status=?, updated_at=? WHERE id=? AND owner_key=?",
                     (threshold, json.dumps(next_rule, ensure_ascii=False), int(active), status, now, alert_id, owner_key))
        conn.commit()
    return get_alert(owner_key=owner_key, alert_id=alert_id)


def delete_alert(*, owner_key: str, alert_id: int) -> bool:
    ensure_schema()
    with closing(_connect()) as conn:
        cur=conn.execute("DELETE FROM advanced_alerts WHERE id=? AND owner_key=?", (alert_id, owner_key)); conn.commit(); return cur.rowcount>0


def evaluate_alert(*, owner_key: str, alert_id: int, signals: dict[str, Any]) -> dict[str, Any] | None:
    alert=get_alert(owner_key=owner_key, alert_id=alert_id)
    if not alert: return None
    now=datetime.utcnow().isoformat(timespec="seconds")
    typ=alert["alert_type"]; threshold=alert.get("threshold_value"); triggered=False; reason="Koşul henüz oluşmadı"; current=None
    if typ=="price_target":
        current=signals.get("current_price"); triggered=current is not None and float(current)<=float(threshold); reason=f"Fiyat {current} TL ile hedefin altına indi" if triggered else reason
    elif typ=="discount_percent":
        current=signals.get("discount_percent"); triggered=current is not None and float(current)>=float(threshold); reason=f"İndirim %{current} seviyesine ulaştı" if triggered else reason
    elif typ=="stock_back": triggered=bool(signals.get("in_stock")); reason="Ürün yeniden stokta" if triggered else reason
    elif typ=="coupon_available": triggered=bool(signals.get("coupon_available")); reason="Kupon bulundu" if triggered else reason
    elif typ=="campaign_available": triggered=bool(signals.get("campaign_available")); reason="Kampanya bulundu" if triggered else reason
    elif typ=="new_seller": triggered=bool(signals.get("new_seller")); reason="Yeni satıcı eklendi" if triggered else reason
    elif typ=="official_seller": triggered=bool(signals.get("official_seller")); reason="Resmî satıcı teklifi bulundu" if triggered else reason
    elif typ=="value_score":
        current=signals.get("value_score"); triggered=current is not None and float(current)>=float(threshold); reason=f"Değer puanı {current} seviyesine ulaştı" if triggered else reason
    status="READY_FOR_NOTIFICATION" if triggered else "WAITING"
    with closing(_connect()) as conn:
        conn.execute("""UPDATE advanced_alerts SET status=?, last_checked_at=?, last_triggered_at=CASE WHEN ? THEN ? ELSE last_triggered_at END,
                     trigger_count=trigger_count+CASE WHEN ? THEN 1 ELSE 0 END, last_reason=?, updated_at=? WHERE id=? AND owner_key=?""",
                     (status, now, int(triggered), now, int(triggered), reason, now, alert_id, owner_key))
        conn.execute("INSERT INTO advanced_alert_events(alert_id,event_type,reason,current_value,payload_json,created_at) VALUES(?,?,?,?,?,?)",
                     (alert_id, "TRIGGERED" if triggered else "CHECKED", reason, float(current) if current is not None else None, json.dumps(signals, ensure_ascii=False), now))
        conn.commit()
    return {"alert": get_alert(owner_key=owner_key, alert_id=alert_id), "triggered": triggered, "status": status, "reason": reason}


def events(*, owner_key: str, alert_id: int, limit: int = 50) -> list[dict[str, Any]]:
    if not get_alert(owner_key=owner_key, alert_id=alert_id): return []
    with closing(_connect()) as conn:
        return [_row(r) for r in conn.execute("SELECT * FROM advanced_alert_events WHERE alert_id=? ORDER BY id DESC LIMIT ?", (alert_id, max(1,min(limit,100)))).fetchall()]


def admin_summary() -> dict[str, Any]:
    ensure_schema()
    with closing(_connect()) as conn:
        rows=conn.execute("SELECT status, COUNT(*) c FROM advanced_alerts GROUP BY status").fetchall()
        total=conn.execute("SELECT COUNT(*) FROM advanced_alerts").fetchone()[0]
        events_count=conn.execute("SELECT COUNT(*) FROM advanced_alert_events").fetchone()[0]
    return {"engine_version": ENGINE_VERSION, "total": total, "events": events_count, "by_status": {r[0]:r[1] for r in rows}, "notification_delivery": "READY_FOR_NOTIFICATION"}
