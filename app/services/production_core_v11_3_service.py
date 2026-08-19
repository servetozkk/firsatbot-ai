from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.operational_log_service import operational_summary

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "data" / "reports" / "v11_3_0_production_core_report.json"
REQUIRED_PACKAGES = ("fastapi", "sqlalchemy", "uvicorn", "jinja2")


def _version() -> str:
    path = ROOT / "VERSION"
    return path.read_text(encoding="utf-8").strip() if path.exists() else "unknown"


def _database_health() -> dict[str, Any]:
    path = settings.database_path
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "size_mb": round(path.stat().st_size / 1048576, 3) if path.exists() else 0,
        "integrity_check": "missing",
        "foreign_key_violations": None,
        "wal_exists": path.with_name(path.name + "-wal").exists(),
    }
    if not path.exists():
        return result
    try:
        with sqlite3.connect(path) as connection:
            result["integrity_check"] = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            result["foreign_key_violations"] = len(connection.execute("PRAGMA foreign_key_check").fetchall())
            result["journal_mode"] = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def _config_health() -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if settings.is_production:
        if not settings.secret_key_is_strong:
            blockers.append("SECRET_KEY en az 32 karakter olmalı ve varsayılan değer kullanılmamalı.")
        if not settings.admin_access_token:
            blockers.append("ADMIN_ACCESS_TOKEN eksik.")
        if not settings.secure_cookies:
            blockers.append("SECURE_COOKIES production ortamında açık olmalı.")
        if not settings.trusted_hosts:
            blockers.append("TRUSTED_HOSTS boş.")
    else:
        warnings.append("APP_ENV production değil; bu rapor çevrimdışı hazırlık denetimidir.")
    if settings.app_version != _version():
        warnings.append(f"APP_VERSION ({settings.app_version}) ile VERSION ({_version()}) farklı.")
    return {
        "environment": settings.app_env,
        "host": settings.host,
        "port": settings.port,
        "scheduler_enabled": settings.enable_scheduler,
        "csrf_enabled": settings.csrf_enabled,
        "rate_limit_enabled": settings.rate_limit_enabled,
        "secure_cookies": settings.secure_cookies,
        "trusted_host_count": len(settings.trusted_hosts),
        "secret_key_strong": settings.secret_key_is_strong,
        "admin_access_token_present": bool(settings.admin_access_token),
        "blockers": blockers,
        "warnings": warnings,
    }


def _scheduler_health() -> dict[str, Any]:
    try:
        from app.scheduler import get_scan_interval_seconds
        interval = get_scan_interval_seconds()
    except Exception as error:
        return {"enabled": settings.enable_scheduler, "status": "ERROR", "error": str(error)}
    return {
        "enabled": settings.enable_scheduler,
        "status": "CONFIGURED" if settings.enable_scheduler else "DISABLED",
        "scan_interval_seconds": interval,
        "note": "Canlı görev durumu yalnızca çalışan uygulama sürecinde doğrulanabilir.",
    }


def _scraper_health() -> dict[str, Any]:
    try:
        from app.services.scraper_resilience_service import all_store_health
        stores = all_store_health()
        open_circuits = sum(1 for row in stores if str(row.get("circuit_state", "")).casefold() == "open")
        return {"status": "OK" if not open_circuits else "WARNING", "store_count": len(stores), "open_circuit_count": open_circuits, "stores": stores}
    except Exception as error:
        return {"status": "WARNING", "store_count": 0, "open_circuit_count": 0, "error": str(error)}


def _backup_health() -> dict[str, Any]:
    candidates = [ROOT / "backups", ROOT / "data" / "backups"]
    files: list[Path] = []
    for folder in candidates:
        if folder.exists():
            files.extend(path for path in folder.rglob("*") if path.is_file())
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    newest = files[0] if files else None
    return {
        "backup_file_count": len(files),
        "newest_backup": str(newest) if newest else None,
        "newest_backup_age_hours": round((datetime.now(timezone.utc).timestamp() - newest.stat().st_mtime) / 3600, 2) if newest else None,
    }


def _runtime_health() -> dict[str, Any]:
    usage = shutil.disk_usage(ROOT)
    packages = {name: importlib.util.find_spec(name) is not None for name in REQUIRED_PACKAGES}
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "free_disk_gb": round(usage.free / (1024 ** 3), 2),
        "packages": packages,
        "missing_packages": [name for name, present in packages.items() if not present],
    }


def build_production_core_report() -> dict[str, Any]:
    config = _config_health()
    database = _database_health()
    runtime = _runtime_health()
    scheduler = _scheduler_health()
    scraper = _scraper_health()
    operations = operational_summary()
    backup = _backup_health()

    blockers = list(config["blockers"])
    warnings = list(config["warnings"])
    if not database.get("exists"):
        blockers.append("Veritabanı dosyası bulunamadı.")
    elif database.get("integrity_check") != "ok":
        blockers.append("SQLite integrity_check başarısız.")
    if database.get("foreign_key_violations") not in (0, None):
        blockers.append("Foreign key ihlali bulundu.")
    if runtime["missing_packages"]:
        blockers.append("Eksik Python paketleri: " + ", ".join(runtime["missing_packages"]))
    if runtime["free_disk_gb"] < 2:
        blockers.append("Boş disk alanı 2 GB altında.")
    elif runtime["free_disk_gb"] < 5:
        warnings.append("Boş disk alanı 5 GB altında.")
    if backup["backup_file_count"] == 0:
        warnings.append("Yedek dosyası bulunamadı.")
    if operations.get("errors_24h", 0):
        warnings.append(f"Son 24 saatte {operations['errors_24h']} operasyon hatası var.")
    if scraper.get("open_circuit_count", 0):
        warnings.append(f"{scraper['open_circuit_count']} mağazada circuit açık.")

    status = "PRODUCTION_READY"
    if blockers:
        status = "PRODUCTION_BLOCKED"
    elif warnings:
        status = "PRODUCTION_READY_WITH_WARNINGS"

    return {
        "version": _version(),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
        "config": config,
        "database": database,
        "runtime": runtime,
        "scheduler": scheduler,
        "scraper": scraper,
        "operations": operations,
        "backup": backup,
        "read_only": True,
    }


def write_production_core_report(report: dict[str, Any]) -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return REPORT_PATH
