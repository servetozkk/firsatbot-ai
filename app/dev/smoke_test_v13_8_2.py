from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.8.2", "VERSION 13.8.2")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        db_path = Path(td) / "analytics.db"
        os.environ["FIRSATAI_ANALYTICS_DB_PATH"] = str(db_path)
        from app.services.anonymous_analytics_service import dashboard, record_event
        record_event(event_type="search", search_query="rtx laptop", result_count=4, duration_ms=25, metadata={"ip":"1.2.3.4", "filter":"gpu"})
        record_event(event_type="search_no_results", search_query="olmayan ürün", result_count=0)
        record_event(event_type="product_view", product_key="urun-1")
        record_event(event_type="store_click", store_code="amazon")
        data = dashboard(30)
        ok(data["searches"] == 1, "anonim arama kaydı oluşturuluyor")
        ok(data["no_result_searches"] == 1, "sonuç bulunamayan aramalar kaydediliyor")
        ok(data["top_products"][0]["product_key"] == "urun-1", "ürün görüntülenmesi sayılıyor")
        ok(data["top_stores"][0]["store_code"] == "amazon", "mağaza tıklaması sayılıyor")
        with sqlite3.connect(db_path) as conn:
            raw = conn.execute("SELECT metadata_json FROM anonymous_analytics_events WHERE event_type='search'").fetchone()[0]
        ok("ip" not in json.loads(raw), "IP bilgisi saklanmıyor")
        ok(data["privacy"]["stores_email"] is False and data["privacy"]["requires_cookie_id"] is False, "anonim veri ilkesi korunuyor")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8-sig")
    routes = (ROOT / "app/web/anonymous_analytics_routes.py").read_text(encoding="utf-8-sig")
    base = (ROOT / "app/templates/public_base.html").read_text(encoding="utf-8-sig")
    ok("anonymous_analytics_router" in main_text, "analytics router uygulamaya bağlı")
    ok('/api/analytics/v13' in routes and '/admin/analytics' in routes, "analytics API ve admin paneli mevcut")
    ok("anonymous-analytics-v13.js" in base, "anonim analitik istemcisi arayüze bağlı")
    print("\nFırsatAI v13.8.2 Kullanıcı Analitiği smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
