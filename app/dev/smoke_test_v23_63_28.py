from pathlib import Path
import ast
root=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,name):
    if not cond: raise AssertionError(name)
    checks.append(name); print('OK ',name)
main=(root/'main.py').read_text(encoding='utf-8')
generic=(root/'app/scrapers/generic_store.py').read_text(encoding='utf-8')
retail=(root/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
repair=(root/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
ok('23.63.28' in main,'VERSION 23.63.28')
ok('v236328' in main,'runtime endpoint')
ok('mediamarkt-redmi-note15pro-verified-card-price-detail-retry' in main,'architecture')
ok('_verified_price_fallback_v236328' in generic,'generic opt-in hook')
ok('return None' in generic,'default fallback fail-closed')
ok('_verified_card_price_v236328 = None' in retail,'MediaMarkt fallback disabled by default')
ok('V23.63.28 MEDIAMARKT VERIFIED CARD PRICE DETAIL FALLBACK' in retail,'MediaMarkt fallback marker')
ok('5000.0 <= value <= 100000.0' in retail,'plausible phone price bound')
ok('("xiaomi", "redmi", "note", "15", "pro", "256")' in retail,'exact family/storage URL lock')
ok('V23.63.28 MEDIAMARKT PRICE-MISSING RETRY' in repair,'retry marker')
ok('retry_score_v236328 >= 316' in repair,'strong score lock')
ok('len(retry_prices_v236328) == 1' in repair,'single card price lock')
ok('challenge_bypass=False' in repair,'no challenge bypass')
ok('canonical_match' in repair or 'canonical matcher bridge' in repair,'normal canonical path preserved')
ok('V23.63.27 TURKCELL REDMI WATCH 5 ACTIVE STRUCTURED PRICE PROVENANCE' in retail,'Turkcell v23.63.27 preserved')
ok('V23.63.25 N11 SEARCH-CARD DIRECT VERIFIED OFFER' in repair,'N11 v23.63.25 preserved')
ok('V23.63.22' in repair,'HB v23.63.22 preserved')
ok('V23.63.19' in repair,'Idefix v23.63.19 preserved')
for rel in ['main.py','app/scrapers/generic_store.py','app/scrapers/retail_stores.py','app/services/multi_store_offer_repair_v14_service.py','app/services/cross_store_search_service.py']:
    ast.parse((root/rel).read_text(encoding='utf-8')); ok(True,'AST '+rel)
print(f'V23.63.28 MASTER smoke OK {len(checks)}/{len(checks)}')
