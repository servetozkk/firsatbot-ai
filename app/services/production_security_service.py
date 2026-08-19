from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

ROOT = Path(__file__).resolve().parents[2]
SENSITIVE_PATTERN = re.compile(r"(?i)(password|passwd|token|secret|authorization|cookie|session)(\s*[=:]\s*)([^\s,;]+)")


def mask_sensitive_text(value: str) -> str:
    return SENSITIVE_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}***", str(value or ""))


def production_security_report() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    def add(code: str, ok: bool, level: str, message: str) -> None:
        checks.append({"code": code, "ok": bool(ok), "level": level, "message": message})
    add("environment", settings.is_production, "warning", f"APP_ENV={settings.app_env}")
    add("secret_key", settings.secret_key_is_strong, "critical", "SECRET_KEY güçlü ve varsayılan değil.")
    add("admin_token", bool(settings.admin_access_token), "critical", "ADMIN_ACCESS_TOKEN tanımlı.")
    add("secure_cookies", settings.secure_cookies, "warning", "Secure cookie etkin.")
    add("csrf", settings.csrf_enabled, "critical", "Aynı kaynak CSRF kontrolü etkin.")
    add("rate_limit", settings.rate_limit_enabled, "warning", "Rate limit etkin.")
    add("trusted_hosts", bool(settings.trusted_hosts), "warning", "TRUSTED_HOSTS tanımlı.")
    add("database_exists", settings.database_path.exists(), "critical", "Veritabanı dosyası mevcut.")
    critical = sum(1 for item in checks if not item["ok"] and item["level"] == "critical")
    warnings = sum(1 for item in checks if not item["ok"] and item["level"] == "warning")
    return {"status": "BLOCKED" if critical else ("READY_WITH_WARNINGS" if warnings else "READY"), "checked_at": datetime.utcnow().isoformat(timespec="seconds"), "critical_count": critical, "warning_count": warnings, "checks": checks}


def create_database_backup() -> dict[str, Any]:
    source = settings.database_path
    if not source.exists():
        raise FileNotFoundError(f"Veritabanı bulunamadı: {source}")
    backup_dir = ROOT / "data" / "backups" / "production"
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / f"products_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    source_connection = sqlite3.connect(str(source))
    target_connection = sqlite3.connect(str(destination))
    try:
        source_connection.backup(target_connection)
    finally:
        target_connection.close(); source_connection.close()
    verify = sqlite3.connect(str(destination))
    try:
        result = verify.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        verify.close()
    if str(result).casefold() != "ok":
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Yedek bütünlük kontrolü başarısız: {result}")
    return {"path": str(destination), "size_mb": round(destination.stat().st_size / 1024 / 1024, 3), "integrity": "ok"}


def write_security_report() -> Path:
    output = ROOT / "data" / "reports" / "v10_3_security_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(production_security_report(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output
