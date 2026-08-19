from pathlib import Path
import py_compile
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(c,n): checks.append((bool(c),n)); print(("OK   " if c else "FAIL ")+n)
main=(ROOT/"main.py").read_text(encoding="utf-8")
repair=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
ok((ROOT/"VERSION").read_text().strip()=="23.62.93","VERSION 23.62.93")
ok('_RUNTIME_VERSION_V236293 = "23.62.93"' in main,"single runtime v236293")
ok('/api/runtime-identity/v236293' in main,"runtime endpoint v236293")
ok('"runtime_version": _RUNTIME_VERSION_V236293' in main,"force/runtime source v236293")
ok('def _v236293_n11_rendered_phone_search_card_offer' in repair,"N11 rendered phone recovery")
ok('V23.62.93 N11 RENDERED OPTION PREFLIGHT' in repair,"rendered preflight telemetry")
ok('family==source_family and variants==source_variants and storage==source_storage and color==source_color' in repair,"exact identity plus color gate")
ok('int(evidence.get("score") or 0) < 316' in repair,"score316 floor")
ok('BrowserEngine' in repair and 'headless=True' in repair,"bounded headless rendered evidence")
ok('force_attach_candidate_offer' in repair,"normal attach pipeline preserved")
ok('V23.62.91 AMAZON VERIFIED PHONE SEARCH-CARD OFFER' in repair,"Amazon v91 preserved")
ok('security_challenge_bypass": "disabled"' in main,"security bypass disabled")
ok('price_integrity_quarantine": "preserved"' in main,"price integrity preserved")
for p in [ROOT/"main.py",ROOT/"app/services/multi_store_offer_repair_v14_service.py"]: py_compile.compile(str(p),doraise=True)
ok(True,"critical Python compile")
failed=[n for c,n in checks if not c]
print(f"V23.62.93 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
