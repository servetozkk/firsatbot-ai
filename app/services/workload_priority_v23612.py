from __future__ import annotations

from pathlib import Path
from time import time, monotonic
import os
import sqlite3
from typing import Any

# V23.61.6:
# In-memory dict yerine SQLite-backed ortak lease.
# Aynı proje runtime'ındaki farklı thread/process/module instance'ları aynı dosyayı görür.
_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "workload_priority_v23616.db"
_STALE_AFTER_SECONDS = 3600.0


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=10.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_ingestion_priority_lease (
            task_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            queued_epoch REAL NOT NULL,
            running_epoch REAL,
            updated_epoch REAL NOT NULL,
            owner_pid INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workload_priority_meta (
            meta_key TEXT PRIMARY KEY,
            meta_value INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO workload_priority_meta(meta_key, meta_value)
        VALUES ('user_priority_generation', 0)
        """
    )
    return conn


def _cleanup_stale(conn: sqlite3.Connection, now_epoch: float) -> None:
    conn.execute(
        "DELETE FROM user_ingestion_priority_lease WHERE updated_epoch < ?",
        (float(now_epoch) - _STALE_AFTER_SECONDS,),
    )


def mark_user_deep_queued_v23612(task_id: str) -> None:
    key = str(task_id)
    now_epoch = time()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _cleanup_stale(conn, now_epoch)
        row = conn.execute(
            "SELECT queued_epoch FROM user_ingestion_priority_lease WHERE task_id=?",
            (key,),
        ).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO user_ingestion_priority_lease
                (task_id,state,queued_epoch,running_epoch,updated_epoch,owner_pid)
                VALUES (?,?,?,?,?,?)
                """,
                (key, "QUEUED", now_epoch, None, now_epoch, os.getpid()),
            )
            # V23.61.7: kullanıcı işi sisteme girdiği anda monoton generation artar.
            # Lease daha sonra yanlışlıkla temizlense bile background batch bu olayı
            # generation değişiminden görür.
            conn.execute(
                """
                UPDATE workload_priority_meta
                SET meta_value = meta_value + 1
                WHERE meta_key='user_priority_generation'
                """
            )
        else:
            # İlk kullanıcı geliş zamanını koru.
            conn.execute(
                """
                UPDATE user_ingestion_priority_lease
                SET state='QUEUED', updated_epoch=?, owner_pid=?
                WHERE task_id=?
                """,
                (now_epoch, os.getpid(), key),
            )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def mark_user_deep_running_v23612(task_id: str) -> float:
    key = str(task_id)
    now_epoch = time()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _cleanup_stale(conn, now_epoch)
        row = conn.execute(
            "SELECT queued_epoch FROM user_ingestion_priority_lease WHERE task_id=?",
            (key,),
        ).fetchone()
        queued_epoch = float(row[0]) if row else now_epoch
        if row is None:
            conn.execute(
                """
                INSERT INTO user_ingestion_priority_lease
                (task_id,state,queued_epoch,running_epoch,updated_epoch,owner_pid)
                VALUES (?,?,?,?,?,?)
                """,
                (key, "RUNNING", queued_epoch, now_epoch, now_epoch, os.getpid()),
            )
        else:
            conn.execute(
                """
                UPDATE user_ingestion_priority_lease
                SET state='RUNNING', running_epoch=?, updated_epoch=?, owner_pid=?
                WHERE task_id=?
                """,
                (now_epoch, now_epoch, os.getpid(), key),
            )
        conn.execute("COMMIT")
        return max(0.0, now_epoch - queued_epoch)
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def mark_user_deep_done_v23612(task_id: str) -> None:
    key = str(task_id)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "DELETE FROM user_ingestion_priority_lease WHERE task_id=?",
            (key,),
        )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def user_deep_priority_active_v23612() -> bool:
    now_epoch = time()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _cleanup_stale(conn, now_epoch)
        row = conn.execute(
            "SELECT 1 FROM user_ingestion_priority_lease LIMIT 1"
        ).fetchone()
        conn.execute("COMMIT")
        return row is not None
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        # Fail-safe: priority coordination hatasında background işi başlatmak yerine
        # user ingestion lehine yield et.
        return True
    finally:
        conn.close()


def user_priority_generation_v23617() -> int:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT meta_value FROM workload_priority_meta WHERE meta_key='user_priority_generation'"
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def user_deep_priority_snapshot_v23612() -> dict[str, Any]:
    now_epoch = time()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _cleanup_stale(conn, now_epoch)
        rows = conn.execute(
            """
            SELECT task_id,state,queued_epoch,running_epoch,updated_epoch,owner_pid
            FROM user_ingestion_priority_lease
            ORDER BY queued_epoch ASC
            """
        ).fetchall()
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()

    tasks = []
    for task_id,state,queued_epoch,running_epoch,updated_epoch,owner_pid in rows:
        tasks.append({
            "task_id": str(task_id),
            "state": str(state),
            "queue_age_seconds": round(max(0.0, now_epoch-float(queued_epoch)),3),
            "running_age_seconds": (
                round(max(0.0, now_epoch-float(running_epoch)),3)
                if running_epoch is not None else None
            ),
            "last_update_age_seconds": round(max(0.0, now_epoch-float(updated_epoch)),3),
            "owner_pid": int(owner_pid),
        })
    return {
        "active": bool(tasks),
        "count": len(tasks),
        "backend": "sqlite-cross-process",
        "db_path": str(_DB_PATH),
        "priority_generation": user_priority_generation_v23617(),
        "tasks": tasks,
    }


def clear_all_priority_leases_v23616() -> None:
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM user_ingestion_priority_lease")
        conn.execute("COMMIT")
    finally:
        conn.close()
