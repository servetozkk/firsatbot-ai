from pathlib import Path
import py_compile
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[]
def ok(v,n):
    checks.append((bool(v),n)); print(('OK   ' if v else 'FAIL ')+n)
ok((ROOT/'VERSION').read_text().strip()=='23.62.96','VERSION 23.62.96')
ok('_RUNTIME_VERSION_V236296 = "23.62.96"' in main,'single runtime v236296')
ok('/api/runtime-identity/v236296' in main,'runtime endpoint v236296')
ok('/api/runtime-soak-stability/v236296' in main,'soak endpoint v236296')
ok('"runtime_version": _RUNTIME_VERSION_V236296' in main,'force/runtime source v236296')
ok('V23.62.96 IDEFIX CANONICAL-STRONG-QUERY-ONLY' in search,'Idefix canonical strong query telemetry')
ok('definition.code == "idefix"' in search and 'search_query,' in search,'Idefix search_query-first policy')
ok('idefix_navigation_budget_v236236 = 6_500' in search,'Idefix 6.5s bounded navigation')
ok('min(2_500, idefix_remaining_ms_v236236)' in search,'Idefix 2.5s bounded anchor wait')
ok('[data-testid*="product"] a[href]' in search and '[data-product-url]' in search,'Idefix adapter selector union probe')
ok('V23.62.96 IDEFIX ADAPTER-ANCHOR PROBE' in search,'Idefix adapter-anchor telemetry')
ok('_v236291_amazon_verified_phone_search_card_offer' in repair,'Amazon v91 preserved')
ok('V23.62.95 N11 CARD-PRICE EVIDENCE REPARSE' in repair,'N11 v95 preserved')
ok('security_challenge_bypass' in main and '"disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine' in main and '"preserved"' in main,'price integrity preserved')
for f in [ROOT/'main.py', ROOT/'app/services/cross_store_search_service.py', ROOT/'app/services/multi_store_offer_repair_v14_service.py']:
    py_compile.compile(str(f),doraise=True)
ok(True,'critical Python compile')
failed=[n for v,n in checks if not v]
print(f"V23.62.96 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
