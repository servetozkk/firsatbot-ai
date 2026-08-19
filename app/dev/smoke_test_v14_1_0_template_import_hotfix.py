from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "14.1.0", "VERSION 14.1.0 korunuyor")
    route = (ROOT / "app/web/scraper_operations_routes.py").read_text(encoding="utf-8-sig")
    ok("from fastapi.templating import Jinja2Templates" in route, "Jinja2Templates doğrudan kullanılıyor")
    ok("app.web.template_helpers" not in route, "olmayan template_helpers importu kaldırıldı")
    ok("admin_scraper_operations_v14.html" in route, "scraper operasyon template bağlantısı korunuyor")
    import app.web.scraper_operations_routes as module
    ok(module.router is not None, "scraper operasyon route modülü import ediliyor")
    print("\nFırsatAI v14.1.0 scraper template import hotfix smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
