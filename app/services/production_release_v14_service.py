from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.beta_readiness_service import build_beta_readiness

ENGINE_VERSION = "14.0.0"
ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "data" / "reports" / "v14_0_0_production_release.json"
ENV_TEMPLATE_PATH = ROOT / ".env.v14.production.example"

REQUIRED_FILES = [
    "app/web/health_v12_routes.py",
    "app/middleware/production.py",
    "app/middleware/security.py",
    "app/middleware/api_cache.py",
    "app/services/public_beta_service.py",
    "app/services/beta_readiness_service.py",
    "app/ops/sqlite_backup_v12.py",
    "app/database/session.py",
]


def _database_health() -> dict[str, Any]:
    path = Path(settings.database_path)
    if not path.exists():
        return {"ok": False, "path": str(path), "integrity": "missing", "foreign_key_violations": None}
    try:
        with closing(sqlite3.connect(str(path), timeout=5)) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        return {
            "ok": integrity == "ok" and foreign_keys == 0,
            "path": str(path),
            "integrity": integrity,
            "foreign_key_violations": foreign_keys,
            "size_bytes": path.stat().st_size,
        }
    except sqlite3.Error as exc:
        return {"ok": False, "path": str(path), "error": f"{type(exc).__name__}: {exc}"}


def _deployment_requirements() -> list[str]:
    requirements: list[str] = []
    if settings.app_env != "production":
        requirements.append("APP_ENV=production")
    if not settings.secret_key_is_strong:
        requirements.append("SECRET_KEY (en az 32 karakter)")
    if not settings.admin_access_token:
        requirements.append("ADMIN_ACCESS_TOKEN")
    if not settings.secure_cookies:
        requirements.append("SECURE_COOKIES=1")
    if not settings.trusted_hosts:
        requirements.append("TRUSTED_HOSTS")
    return requirements


def build_production_release(write_report: bool = False) -> dict[str, Any]:
    beta = build_beta_readiness(write_report=False)
    database = _database_health()
    missing_files = [item for item in REQUIRED_FILES if not (ROOT / item).exists()]
    code_blockers: list[str] = []
    if beta.get("status") != "BETA_READY":
        code_blockers.append("Beta readiness BETA_READY değil")
    if not database.get("ok"):
        code_blockers.append("Veritabanı bütünlük kontrolü başarısız")
    if missing_files:
        code_blockers.append("Eksik üretim dosyaları: " + ", ".join(missing_files))
    if not ENV_TEMPLATE_PATH.exists():
        code_blockers.append("Production env şablonu eksik")

    deployment_requirements = _deployment_requirements()
    release_status = "PRODUCTION_RELEASE_READY" if not code_blockers else "PRODUCTION_RELEASE_BLOCKED"
    deployment_status = "PRODUCTION_READY" if not code_blockers and not deployment_requirements else "PRODUCTION_CONFIGURATION_REQUIRED"
    payload = {
        "engine_version": ENGINE_VERSION,
        "release_status": release_status,
        "deployment_status": deployment_status,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environment": settings.app_env,
        "database": database,
        "beta_readiness": beta.get("status"),
        "module_summary": beta.get("summary", {}),
        "source_metrics": beta.get("source_metrics", {}),
        "required_files": {"total": len(REQUIRED_FILES), "missing": missing_files},
        "security": {
            "csrf_enabled": settings.csrf_enabled,
            "rate_limit_enabled": settings.rate_limit_enabled,
            "secure_cookies": settings.secure_cookies,
            "secret_key_strong": settings.secret_key_is_strong,
            "admin_token_configured": bool(settings.admin_access_token),
            "trusted_hosts": list(settings.trusted_hosts),
        },
        "operations": {
            "health_live": "/health/live",
            "health_ready": "/health/ready",
            "production_status": "/api/production/v14",
            "admin_dashboard": "/admin/production-release",
            "backup_tool": "SQLITE_YEDEK_AL.bat",
            "env_template": ENV_TEMPLATE_PATH.name,
        },
        "code_blockers": code_blockers,
        "deployment_requirements": deployment_requirements,
    }
    if write_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
