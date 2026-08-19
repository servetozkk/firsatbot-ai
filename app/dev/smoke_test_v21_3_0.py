from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
main = (ROOT / "main.py").read_text(encoding="utf-8")
config = (ROOT / "app/core/config.py").read_text(encoding="utf-8")
feed = (ROOT / "app/services/catalog_feed_v213_service.py").read_text(encoding="utf-8")
route = (ROOT / "app/web/catalog_feed_v213_routes.py").read_text(encoding="utf-8")

assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "21.3.0"
assert '/api/runtime-identity/v213' in main
assert 'catalog_feed_v213_router' in main
assert 'start_catalog_feed' in main and 'stop_catalog_feed' in main
assert 'CATALOG_FEED_ENABLED' in config
assert 'repair_product_across_stores' in feed
assert 'product_from_global_product' in feed
assert 'FIRSATAI_CATALOG_FEED_ENGINE' in feed
assert 'SECURITY_CHALLENGE' not in feed  # store-specific challenge remains isolated in existing repair layer
assert 'prefix="/api/catalog-feed/v213"' in route
print('OK v21.3 catalog feed engine smoke')
