from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["system"])
_started_at = time.time()


def _database_status() -> dict[str, object]:
    path: Path = settings.database_path
    result: dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2) if path.exists() else 0,
        "ok": False,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path, timeout=3) as connection:
            connection.execute("SELECT 1").fetchone()
        result["ok"] = True
    except sqlite3.Error as error:
        result["error"] = str(error)
    return result


@router.get("/health/ready", include_in_schema=False)
def readiness() -> dict[str, object]:
    database = _database_status()
    return {
        "status": "ready" if database["ok"] else "degraded",
        "version": settings.app_version,
        "environment": settings.app_env,
        "scheduler_enabled": settings.enable_scheduler,
        "database": database,
        "uptime_seconds": int(time.time() - _started_at),
        "process_id": os.getpid(),
    }


@router.get("/api/system/status", include_in_schema=False)
def system_status() -> dict[str, object]:
    return readiness()
