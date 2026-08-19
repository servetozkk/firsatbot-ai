from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.operational_log_service import operational_summary
from app.services.production_security_service import (
    create_database_backup,
    production_security_report,
)
from app.services.scraper_resilience_service import (
    all_store_health,
    read_dead_letters,
)
from app.services.v10_release_service import (
    build_release_diagnostics,
    repair_release_integrity,
)


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "data" / "reports" / "v11_stable_report.json"
VERSION = "11.0.0"


def _database_integrity() -> dict[str, Any]:
    database = settings.database_path
    if not database.exists():
        return {
            "ok": False,
            "integrity": "database_missing",
            "foreign_key_errors": -1,
            "path": str(database),
        }

    connection = sqlite3.connect(str(database))
    try:
        integrity = str(
            connection.execute("PRAGMA integrity_check").fetchone()[0]
        )
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
    finally:
        connection.close()

    return {
        "ok": integrity.casefold() == "ok" and not foreign_keys,
        "integrity": integrity,
        "foreign_key_errors": len(foreign_keys),
        "path": str(database),
        "size_mb": round(database.stat().st_size / 1024 / 1024, 3),
    }


def _source_checks() -> list[dict[str, Any]]:
    required = {
        "main": ROOT / "main.py",
        "global_catalog": ROOT / "app/services/global_catalog_search_service.py",
        "price_history": ROOT / "app/services/global_price_history_service.py",
        "price_alert": ROOT / "app/services/global_price_alert_service.py",
        "operations": ROOT / "app/services/operational_log_service.py",
        "scraper_resilience": ROOT / "app/services/scraper_resilience_service.py",
        "security": ROOT / "app/services/production_security_service.py",
        "release": ROOT / "app/services/v10_release_service.py",
    }
    rows = []
    for code, path in required.items():
        rows.append(
            {
                "code": code,
                "ok": path.exists() and path.stat().st_size > 0,
                "path": str(path),
            }
        )
    return rows


def build_stable_report(
    db,
    *,
    create_backup: bool = False,
    repair: bool = False,
    live_application: bool = False,
) -> dict[str, Any]:
    repair_result = repair_release_integrity(db) if repair else None
    release = build_release_diagnostics(
        db,
        require_live_scheduler=live_application,
    )
    security = production_security_report()
    database = _database_integrity()
    source_checks = _source_checks()
    scraper_health = all_store_health()
    dead_letters = read_dead_letters(2000)
    operations = operational_summary()

    backup: dict[str, Any] | None = None
    backup_error: str | None = None
    if create_backup:
        try:
            backup = create_database_backup()
        except Exception as error:  # noqa: BLE001
            backup_error = f"{type(error).__name__}: {error}"

    source_failures = sum(1 for item in source_checks if not item["ok"])
    open_circuits = sum(
        1 for item in scraper_health
        if item.get("status") == "CIRCUIT_OPEN"
    )
    retryable_dead_letters = sum(
        1 for item in dead_letters
        if item.get("retryable") and item.get("status") == "PENDING"
    )

    stable_critical = {
        "release_data_errors": int(release["summary"]["critical_count"]),
        "database_integrity": 0 if database["ok"] else 1,
        "missing_core_sources": source_failures,
        "backup_validation": 1 if create_backup and backup is None else 0,
    }
    stable_warnings = {
        "release_quality_warnings": int(release["summary"]["warning_count"]),
        "open_scraper_circuits": open_circuits,
        "retryable_dead_letters": retryable_dead_letters,
        "operation_errors_24h": int(operations.get("errors_24h", 0)),
    }

    stable_critical_count = sum(stable_critical.values())
    stable_warning_count = sum(stable_warnings.values())
    if stable_critical_count:
        stable_status = "STABLE_BLOCKED"
    elif stable_warning_count:
        stable_status = "STABLE_READY_WITH_WARNINGS"
    else:
        stable_status = "STABLE_READY"

    production_blockers = int(security.get("critical_count", 0))
    production_warnings = int(security.get("warning_count", 0))
    if stable_critical_count or production_blockers:
        production_status = "PRODUCTION_BLOCKED"
    elif stable_warning_count or production_warnings:
        production_status = "PRODUCTION_READY_WITH_WARNINGS"
    else:
        production_status = "PRODUCTION_READY"

    return {
        "version": VERSION,
        "checked_at": datetime.utcnow().isoformat(timespec="seconds"),
        "mode": "LIVE_APPLICATION" if live_application else "OFFLINE_VALIDATION",
        "stable_status": stable_status,
        "production_status": production_status,
        "stable_summary": {
            "critical_count": stable_critical_count,
            "warning_count": stable_warning_count,
            "global_products": release["summary"]["global_products"],
            "active_offers": release["summary"]["active_offers"],
            "multi_store_products": release["summary"]["multi_store_products"],
        },
        "stable_critical": stable_critical,
        "stable_warnings": stable_warnings,
        "release": release,
        "security": security,
        "database_integrity": database,
        "source_checks": source_checks,
        "scraper": {
            "stores": scraper_health,
            "open_circuit_count": open_circuits,
            "dead_letter_count": len(dead_letters),
            "retryable_dead_letter_count": retryable_dead_letters,
        },
        "operations": operations,
        "backup": backup,
        "backup_error": backup_error,
        "automatic_repair": repair_result,
    }


def write_stable_report(report: dict[str, Any]) -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return REPORT_PATH
