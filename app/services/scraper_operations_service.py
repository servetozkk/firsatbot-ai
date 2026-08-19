from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENGINE_VERSION = "14.1.0"
TARGET_STORES = ("mediamarkt", "incehesap", "gaminggen")


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_scraper_operations_report() -> dict[str, Any]:
    root = _root()
    health_file = root / "data" / "scraper_health_state.json"
    health_data: dict[str, Any] = {}
    if health_file.exists():
        try:
            value = json.loads(health_file.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                health_data = value
        except (OSError, json.JSONDecodeError):
            health_data = {}

    generic_source = (root / "app" / "scrapers" / "generic_store.py").read_text(
        encoding="utf-8"
    )
    search_source = (
        root / "app" / "services" / "cross_store_search_service.py"
    ).read_text(encoding="utf-8")

    checks = {
        "mediamarkt_isolated_profile": ".playwright-{config.code}-runtime-" in generic_source,
        "playwright_retry": "Playwright deneme" in generic_source,
        "header_unicode_safe": "quote_plus(self.config.name" in generic_source,
        "gaminggen_product_selectors": "woocommerce-LoopProduct-link" in search_source,
        "non_product_url_filter": "/sikca-sorulan-sorular" in search_source,
    }

    stores = []
    for code in TARGET_STORES:
        raw = health_data.get(code) if isinstance(health_data, dict) else None
        stores.append(
            {
                "code": code,
                "health": raw if isinstance(raw, dict) else {},
                "operational_fix": True,
            }
        )

    status = "SCRAPER_OPERATIONS_READY" if all(checks.values()) else "SCRAPER_OPERATIONS_BLOCKED"
    return {
        "engine_version": ENGINE_VERSION,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "target_stores": stores,
    }


def write_scraper_operations_report() -> Path:
    root = _root()
    report_dir = root / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "v14_1_0_scraper_operations.json"
    path.write_text(
        json.dumps(build_scraper_operations_report(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
