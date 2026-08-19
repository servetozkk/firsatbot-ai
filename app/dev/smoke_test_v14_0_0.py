from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]

def ok(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    ok((ROOT / "VERSION").read_text(encoding="utf-8-sig").strip() == "14.0.0", "VERSION 14.0.0")
    from app.services.production_release_v14_service import build_production_release
    report = build_production_release(write_report=True)
    ok(report["release_status"] == "PRODUCTION_RELEASE_READY", "production release kod durumu hazır")
    ok(report["beta_readiness"] == "BETA_READY", "Public Beta hazırlığı korunuyor")
    ok(report["database"].get("integrity") == "ok", "SQLite integrity başarılı")
    ok(report["database"].get("foreign_key_violations") == 0, "foreign key ihlali yok")
    ok(report["required_files"]["missing"] == [], "üretim için zorunlu dosyalar mevcut")
    ok((ROOT / ".env.v14.production.example").exists(), "production env şablonu mevcut")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="ignore")
    ok("production_release_v14_router" in main_text, "production release router uygulamaya bağlı")
    route_text = (ROOT / "app/web/production_release_v14_routes.py").read_text(encoding="utf-8")
    ok('/api/production/v14' in route_text, "production durum API mevcut")
    ok('/admin/production-release' in route_text, "production admin paneli mevcut")
    report_path = ROOT / "data/reports/v14_0_0_production_release.json"
    ok(report_path.exists() and json.loads(report_path.read_text(encoding="utf-8"))["release_status"] == "PRODUCTION_RELEASE_READY", "production release raporu oluşturuldu")
    print("\nFırsatAI v14.0.0 Production Release smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
