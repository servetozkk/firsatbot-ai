from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.production_core_v11_3_service import build_production_core_report

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "data" / "reports" / "v11_3_1_production_warning_resolution.json"
ENV_TEMPLATE_PATH = ROOT / ".env.v11_3_1.production.example"


def _version() -> str:
    path = ROOT / "VERSION"
    return path.read_text(encoding="utf-8").strip() if path.exists() else "unknown"


def _deployment_requirements() -> list[dict[str, Any]]:
    requirements: list[dict[str, Any]] = []
    if not settings.is_production:
        requirements.append({
            "code": "ACTIVATE_PRODUCTION_PROFILE",
            "severity": "deployment_action",
            "message": "Canlı sunucuda APP_ENV=production profili etkinleştirilmeli.",
            "resolved_in_current_environment": False,
        })
    if not settings.secret_key_is_strong:
        requirements.append({
            "code": "SET_STRONG_SECRET_KEY",
            "severity": "deployment_action" if not settings.is_production else "blocker",
            "message": "Canlı ortamda en az 32 karakterlik rastgele SECRET_KEY kullanılmalı.",
            "resolved_in_current_environment": False,
        })
    if not settings.admin_access_token:
        requirements.append({
            "code": "SET_ADMIN_ACCESS_TOKEN",
            "severity": "deployment_action" if not settings.is_production else "blocker",
            "message": "Canlı ortamda uzun ve rastgele ADMIN_ACCESS_TOKEN tanımlanmalı.",
            "resolved_in_current_environment": False,
        })
    if not settings.secure_cookies:
        requirements.append({
            "code": "ENABLE_SECURE_COOKIES",
            "severity": "deployment_action" if not settings.is_production else "blocker",
            "message": "HTTPS kullanılan canlı ortamda SECURE_COOKIES=1 olmalı.",
            "resolved_in_current_environment": False,
        })
    return requirements


def _write_env_template() -> Path:
    content = "\n".join([
        "# FırsatAI v11.3.1 production örneği",
        f"APP_NAME={settings.app_name}",
        f"APP_VERSION={_version()}",
        "APP_ENV=production",
        "APP_HOST=127.0.0.1",
        f"APP_PORT={settings.port}",
        "ENABLE_SCHEDULER=1",
        "SECRET_KEY=BURAYA_EN_AZ_32_KARAKTER_RASTGELE_ANAHTAR",
        "ADMIN_ACCESS_TOKEN=BURAYA_UZUN_RASTGELE_ADMIN_ANAHTARI",
        "SECURE_COOKIES=1",
        "CSRF_ENABLED=1",
        "RATE_LIMIT_ENABLED=1",
        "TRUSTED_HOSTS=alanadiniz.com,www.alanadiniz.com",
        "",
    ])
    ENV_TEMPLATE_PATH.write_text(content, encoding="utf-8")
    return ENV_TEMPLATE_PATH


def build_warning_resolution_report() -> dict[str, Any]:
    core = build_production_core_report()
    original_warnings = list(core.get("warnings", []))
    operational_warnings = [
        warning for warning in original_warnings
        if not warning.startswith("APP_ENV production değil")
        and not warning.startswith("APP_VERSION (")
    ]

    version_matches = settings.app_version == _version()
    blockers = list(core.get("blockers", []))
    if not version_matches and settings.is_production:
        blockers.append(f"APP_VERSION ({settings.app_version}) ile VERSION ({_version()}) farklı.")

    if blockers:
        status = "PRODUCTION_BLOCKED"
    elif operational_warnings:
        status = "PRODUCTION_READY_WITH_WARNINGS" if settings.is_production else "PRODUCTION_READY_FOR_DEPLOYMENT_WITH_WARNINGS"
    else:
        status = "PRODUCTION_READY" if settings.is_production else "PRODUCTION_READY_FOR_DEPLOYMENT"

    template = _write_env_template()
    return {
        "version": _version(),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "environment": settings.app_env,
        "production_profile_active": settings.is_production,
        "app_version": settings.app_version,
        "version_matches": version_matches,
        "blocker_count": len(blockers),
        "warning_count": len(operational_warnings),
        "blockers": blockers,
        "warnings": operational_warnings,
        "resolved_warning_causes": {
            "development_environment_reclassified": any(w.startswith("APP_ENV production değil") for w in original_warnings),
            "app_version_default_fixed": version_matches,
        },
        "deployment_requirements": _deployment_requirements(),
        "production_env_template": str(template),
        "core_report": core,
        "read_only": True,
    }


def write_warning_resolution_report(report: dict[str, Any]) -> Path:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return REPORT_PATH
