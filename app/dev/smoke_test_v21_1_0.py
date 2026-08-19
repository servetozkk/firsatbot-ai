from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "21.1.0"
assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == "21.1.0"

routes = (ROOT / "app/web/price_comparison_v21_routes.py").read_text(encoding="utf-8")
service = (ROOT / "app/services/price_comparison_core_v21_service.py").read_text(encoding="utf-8")
main = (ROOT / "main.py").read_text(encoding="utf-8")
product_html = (ROOT / "app/templates/price_comparison_product_v21.html").read_text(encoding="utf-8")
search_html = (ROOT / "app/templates/price_comparison_search_v21.html").read_text(encoding="utf-8")

assert 'prefix="/fiyat-karsilastirma"' in routes
assert '"/urun/{global_product_id}"' in routes
assert 'name="price_comparison_product_v21.html"' in routes
assert 'name="price_comparison_search_v21.html"' in routes
assert '"detail_url": f"/fiyat-karsilastirma/urun/{product.id}"' in service
assert '"engine_version": "21.1.0"' in service
assert '/api/runtime-identity/v211' in main
assert 'Mağazaya Git' in product_html
assert 'canlı tarama yok' in product_html
assert 'Fiyatları Bul' in search_html
# Public UI routes only call catalog service functions; repair/scraper is not invoked here.
assert 'multi_store' not in routes.casefold()
assert 'scrape(' not in routes.casefold()
print('OK v21.1.0 price comparison UI smoke test')
