from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENGINE_VERSION = "13.8.3"
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "products.db"
REPORT_PATH = ROOT / "data" / "reports" / "v13_8_3_beta_readiness.json"

MODULES = {
    "smart_search": ["app/web/smart_search_routes.py", "app/services/smart_search_service.py"],
    "advanced_filters": ["app/services/advanced_filter_service.py"],
    "advanced_sort": ["app/services/advanced_sort_service.py"],
    "compare_2": ["app/templates/product_group_compare_v2.html", "app/web/product_group_routes.py"],
    "campaign_center": ["app/web/campaign_center_routes.py"],
    "coupon_system": ["app/web/coupon_center_routes.py"],
    "stock_tracking": ["app/web/stock_tracking_routes.py"],
    "new_products": ["app/web/new_products_routes.py"],
    "seo_urls": ["app/services/seo_url_service.py"],
    "schema_org": ["app/services/schema_org_service.py"],
    "xml_sitemap": ["app/web/sitemap_routes.py"],
    "breadcrumb": ["app/services/breadcrumb_service.py"],
    "landing_pages": ["app/web/landing_page_routes.py"],
    "performance": ["app/web/performance_v13_routes.py"],
    "api_cache": ["app/middleware/api_cache.py", "app/web/api_cache_routes.py"],
    "image_optimization": ["app/services/image_optimization_v13.py"],
    "catalog_scaling": ["app/web/catalog_scaling_routes.py"],
    "store_ecosystem": ["app/web/store_ecosystem_v13_routes.py"],
    "advanced_alerts": ["app/web/advanced_alert_routes.py"],
    "anonymous_analytics": ["app/web/anonymous_analytics_routes.py"],
}


def _module_state(files: list[str]) -> dict[str, Any]:
    missing = [item for item in files if not (ROOT / item).exists()]
    return {"status": "ok" if not missing else "missing", "files": files, "missing": missing}


def _db_health() -> dict[str, Any]:
    if not DB_PATH.exists():
        return {"integrity": "missing", "foreign_key_violations": None, "path": str(DB_PATH)}
    conn = sqlite3.connect(str(DB_PATH))
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        return {"integrity": integrity, "foreign_key_violations": fk, "path": str(DB_PATH), "size_bytes": DB_PATH.stat().st_size}
    finally:
        conn.close()


def _source_metrics() -> dict[str, int]:
    main = (ROOT / "main.py").read_text(encoding="utf-8", errors="ignore") if (ROOT / "main.py").exists() else ""
    route_files = list((ROOT / "app" / "web").glob("*routes.py")) + list((ROOT / "app" / "routes").glob("*.py"))
    templates = list((ROOT / "app" / "templates").glob("*.html"))
    api_tokens = 0
    route_tokens = 0
    for file in route_files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        api_tokens += text.count('@router.get("/api/') + text.count('@router.post("/api/') + text.count('@router.put("/api/') + text.count('@router.delete("/api/')
        route_tokens += text.count("@router.")
    return {"included_routers": main.count("app.include_router("), "route_files": len(route_files), "routes": route_tokens, "api_routes": api_tokens, "templates": len(templates)}


def build_beta_readiness(write_report: bool = False) -> dict[str, Any]:
    modules = {name: _module_state(files) for name, files in MODULES.items()}
    database = _db_health()
    metrics = _source_metrics()
    missing_modules = [name for name, item in modules.items() if item["status"] != "ok"]
    blockers = []
    if missing_modules:
        blockers.append(f"Eksik modül: {', '.join(missing_modules)}")
    if database.get("integrity") != "ok":
        blockers.append("SQLite integrity başarısız")
    if database.get("foreign_key_violations") not in (0, None):
        blockers.append("Foreign key ihlali var")
    status = "BETA_READY" if not blockers else "BETA_BLOCKED"
    payload = {
        "engine_version": ENGINE_VERSION,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "modules": modules,
        "summary": {"total_modules": len(modules), "healthy_modules": len(modules) - len(missing_modules), "missing_modules": len(missing_modules), "blocker_count": len(blockers)},
        "database": database,
        "source_metrics": metrics,
        "blockers": blockers,
        "public_beta_gate": "READY" if status == "BETA_READY" else "NOT_READY",
    }
    if write_report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
