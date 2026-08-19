from pathlib import Path
import py_compile
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[]
def ok(c,n):
    checks.append((n,bool(c))); print(('OK   ' if c else 'FAIL ')+n)
ok((ROOT/'VERSION').read_text().strip()=='23.62.94','VERSION 23.62.94')
ok('_RUNTIME_VERSION_V236294 = "23.62.94"' in main,'single runtime v236294')
ok('/api/runtime-identity/v236294' in main,'runtime endpoint v236294')
ok('"runtime_version": _RUNTIME_VERSION_V236294' in main,'force/runtime source v236294')
ok('evidence.get("card_prices") or evidence.get("price_values")' in repair,'N11 card_prices evidence contract')
ok('V23.62.94 N11 RENDERED RECOVERY GUARD' in repair,'recovery guard telemetry')
ok('V23.62.94 N11 RENDERED OPTION PREFLIGHT' in repair,'rendered preflight telemetry')
ok('V23.62.94 N11 RENDERED EXACT-COLOR SEARCH-CARD RECOVERY' in repair,'exact-color recovery telemetry')
ok('force_attach_candidate_offer' in repair,'normal attach pipeline preserved')
ok('amazon_phone_search_card_offer": "v23.62.91-preserved"' in main,'Amazon v91 preserved')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
try:
    py_compile.compile(str(ROOT/'main.py'),doraise=True); py_compile.compile(str(ROOT/'app/services/multi_store_offer_repair_v14_service.py'),doraise=True); c=True
except Exception as e:
    print(e); c=False
ok(c,'critical Python compile')
failed=[n for n,c in checks if not c]
print(f"V23.62.94 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
