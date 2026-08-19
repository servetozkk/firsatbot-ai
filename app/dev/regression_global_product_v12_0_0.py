from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main() -> int:
    route_file = ROOT / "app" / "web" / "global_product_routes.py"
    ok(route_file.exists(), "global ürün router dosyası mevcut")

    main_text = (ROOT / "main.py").read_text(encoding="utf-8-sig")
    ok("global_product_router" in main_text, "global ürün router main.py içine bağlı")
    ok("app.include_router(global_product_router)" in main_text, "/urun router uygulamaya eklendi")

    template = (ROOT / "app" / "templates" / "product_group_detail_v4.html").read_text(encoding="utf-8-sig")
    ok('/urun/{{ comparison.identity_key }}?variant=' in template, "varyant bağlantıları kanonik /urun yolunu kullanıyor")

    search_service = (ROOT / "app" / "services" / "global_catalog_search_service.py").read_text(encoding="utf-8-sig")
    ok("f'/urun/{p.identity_key}'" in search_service or 'f"/urun/{p.identity_key}"' in search_service, "arama sonuçları kanonik /urun URL üretiyor")

    route_text = route_file.read_text(encoding="utf-8-sig")
    ok('APIRouter(prefix="/urun"' in route_text, "global ürün router /urun prefix kullanıyor")
    ok('@router.get("/{identity_key}"' in route_text, "/urun/{identity_key} endpoint tanımlı")

    legacy_route = (ROOT / "app" / "web" / "product_group_routes.py").read_text(encoding="utf-8-sig")
    ok('prefix="/karsilastir"' in legacy_route and '"/{identity_key}"' in legacy_route, "eski karşılaştırma URL geriye uyumlu")
    print("\nv12 global ürün regresyonu başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
