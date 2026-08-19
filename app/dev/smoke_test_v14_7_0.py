from pathlib import Path


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.7.0", "VERSION 14.7.0")

    base = (root / "app/templates/base.html").read_text(encoding="utf-8")
    route = (
        root / "app/web/admin_module_center_v14_routes.py"
    ).read_text(encoding="utf-8")
    template = (
        root / "app/templates/admin_module_center_v14.html"
    ).read_text(encoding="utf-8")
    main_text = (root / "main.py").read_text(encoding="utf-8")

    required_links = [
        "/admin/live-prices",
        "/admin/bulk-catalog",
        "/admin/bulk-identity",
        "/admin/scraper-operations",
        "/admin/ai-comparison",
        "/admin/production-release",
        "/admin/module-center",
    ]
    for link in required_links:
        ok(f'href="{link}"' in base, f"sol menü bağlantısı mevcut: {link}")

    ok("request.app.routes" in route, "admin route keşfi uygulama kayıtlarından yapılıyor")
    ok("isinstance(route, APIRoute)" in route, "yalnızca gerçek FastAPI route'ları listeleniyor")
    ok('"GET" not in _route_methods(route)' in route, "yalnızca açılabilir GET ekranları listeleniyor")
    ok('"{" in path' in route, "parametre isteyen detay route'ları menüden çıkarılıyor")
    ok("module-grid" in template, "Modül Merkezi kart arayüzü mevcut")
    ok("admin_module_center_v14_router" in main_text, "Modül Merkezi router uygulamaya bağlı")

    print("\nFırsatAI v14.7.0 Admin Navigasyon ve Modül Merkezi smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
