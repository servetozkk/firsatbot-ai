from pathlib import Path
import py_compile
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[]
def ok(v,n):
    checks.append((bool(v),n)); print(('OK   ' if v else 'FAIL ')+n)
ok((ROOT/'VERSION').read_text().strip()=='23.62.95','VERSION 23.62.95')
ok('_RUNTIME_VERSION_V236295 = "23.62.95"' in main,'single runtime v236295')
ok('/api/runtime-identity/v236295' in main,'runtime endpoint v236295')
ok('/api/runtime-soak-stability/v236295' in main,'soak endpoint v236295')
ok('"runtime_version": _RUNTIME_VERSION_V236295' in main,'force/runtime source v236295')
ok('_extract_dom_card_prices_v2320' in repair,'N11 label card-price reparse')
ok('V23.62.95 N11 CARD-PRICE EVIDENCE REPARSE' in repair,'price reparse telemetry')
ok('surface_name, title' in repair and 'browser-title' in repair,'dual H1/browser-title exact-color preflight')
ok('V23.62.95 N11 RENDERED OPTION PREFLIGHT' in repair,'rendered preflight telemetry')
ok('V23.62.95 N11 RENDERED EXACT-COLOR SEARCH-CARD RECOVERY' in repair,'exact-color recovery telemetry')
ok('force_attach_candidate_offer(' in repair,'normal attach pipeline preserved')
ok('_v236291_amazon_verified_phone_search_card_offer' in repair,'Amazon v91 preserved')
ok('security_challenge_bypass' in main and '"disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine' in main and '"preserved"' in main,'price integrity preserved')
for f in [ROOT/'main.py', ROOT/'app/services/multi_store_offer_repair_v14_service.py']:
    py_compile.compile(str(f),doraise=True)
ok(True,'critical Python compile')
failed=[n for v,n in checks if not v]
print(f"V23.62.95 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
