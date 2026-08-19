from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[2]

assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "21.0.0"
assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == "21.0.0"
assert (ROOT / "BASLAT_V21_0.bat").exists()

main = (ROOT / "main.py").read_text(encoding="utf-8")
assert "price_comparison_v21_router" in main
assert "/api/runtime-identity/v210" in main

routes = (ROOT / "app/web/price_comparison_v21_routes.py").read_text(encoding="utf-8")
assert "/products/{global_product_id}" in routes
assert "/search" in routes
assert "live_scrape" in routes

service = (ROOT / "app/services/price_comparison_core_v21_service.py").read_text(encoding="utf-8")
assert "CATALOG_FIRST_NO_LIVE_SCRAPE" in service
assert "FRESH" in service and "STALE" in service
assert "repair_endpoint" in service

for rel in (
    "main.py",
    "app/web/price_comparison_v21_routes.py",
    "app/services/price_comparison_core_v21_service.py",
):
    py_compile.compile(str(ROOT / rel), doraise=True)

print("OK v21.0.0 PRICE COMPARISON CORE smoke")
