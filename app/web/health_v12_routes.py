from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.services.operational_log_service import operational_summary

router = APIRouter(prefix="/health", tags=["health"])


def _db_status() -> dict[str, object]:
    path = Path(settings.database_path)
    if not path.exists():
        return {"ok": False, "path": str(path), "error": "database_not_found"}
    try:
        with sqlite3.connect(str(path), timeout=3) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            fk_count = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        return {
            "ok": integrity == "ok" and fk_count == 0,
            "path": str(path),
            "integrity": integrity,
            "foreign_key_violations": fk_count,
        }
    except sqlite3.Error as exc:
        return {"ok": False, "path": str(path), "error": f"{type(exc).__name__}: {exc}"}


@router.get("/live")
def live() -> dict[str, object]:
    return {
        "status": "alive",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@router.get("/ready")
def ready(response: Response) -> dict[str, object]:
    database = _db_status()
    requirements: list[str] = []
    if settings.is_production:
        if not settings.secret_key_is_strong:
            requirements.append("SECRET_KEY")
        if not settings.admin_access_token:
            requirements.append("ADMIN_ACCESS_TOKEN")
        if not settings.secure_cookies:
            requirements.append("SECURE_COOKIES=1")
        if not settings.trusted_hosts:
            requirements.append("TRUSTED_HOSTS")
    ready_state = bool(database.get("ok")) and not requirements
    if not ready_state:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready_state else "not_ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "scheduler_enabled": settings.enable_scheduler,
        "database": database,
        "deployment_requirements": requirements,
        "operations": operational_summary(),
    }
