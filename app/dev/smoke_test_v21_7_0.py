from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
svc=(ROOT/'app/services/smart_catalog_refresh_v217_service.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
assert (ROOT/'VERSION.txt').read_text().strip()=='21.7.0'
assert '/api/runtime-identity/v217' in main
assert 'allowed_store_codes' in cross and 'allowed_store_codes' in repair
assert "'PRODUCT_NOT_FOUND': 12.0" in svc
assert "'SECURITY_CHALLENGE': 6.0" in svc
assert "'SUCCESS': 0.5" in svc
assert 'existing-active-offers-preserved-on-refresh-failure' in main
print('OK v21.7 smart catalog refresh smoke')
