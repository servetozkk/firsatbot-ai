from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'VERSION').read_text(encoding='utf-8').strip()=='21.2.0'
routes=(ROOT/'app/web/product_group_routes.py').read_text(encoding='utf-8')
tpl=(ROOT/'app/templates/product_group_detail_v4.html').read_text(encoding='utf-8')
svc=(ROOT/'app/services/price_comparison_core_v21_service.py').read_text(encoding='utf-8')
main=(ROOT/'main.py').read_text(encoding='utf-8')
assert 'get_product_price_comparison' in routes
assert 'price_comparison_core_v21_2' in routes
assert 'price_comparison_core' in routes
assert 'Fiyat karşılaştırma çekirdeği:' in tpl
assert 'canli scrape' not in tpl.lower() or 'canlı tarama yapılmaz' in tpl
assert 'global_variant_id' in svc
assert 'FRESH_FIRST' in svc and 'LAST_KNOWN_ACTIVE' in svc
assert '/api/runtime-identity/v212' in main
print('OK v21.2.0 existing product detail price comparison integration')
