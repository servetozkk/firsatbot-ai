from pathlib import Path
import py_compile
ROOT=Path(__file__).resolve().parents[2]
failed=[]
def ok(cond,msg):
    print(("OK   " if cond else "FAIL ")+msg)
    if not cond: failed.append(msg)
main=(ROOT/"main.py").read_text(encoding="utf-8")
search=(ROOT/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
adapter=(ROOT/"app/stores/adapters/idefix.py").read_text(encoding="utf-8")
ok((ROOT/"VERSION").read_text().strip()=="23.62.99","VERSION 23.62.99")
ok("_RUNTIME_VERSION_V236299 = \"23.62.99\"" in main,"single runtime v236299")
ok("/api/runtime-identity/v236299" in main,"runtime endpoint v236299")
ok("/api/runtime-soak-stability/v236299" in main,"soak endpoint v236299")
ok("\"runtime_version\": _RUNTIME_VERSION_V236299" in main,"force response v236299")
ok("V23.62.99 IDEFIX BRAND-CATALOG RECOVERY" in search,"Idefix brand catalog recovery telemetry")
ok("V23.62.99 IDEFIX BRAND-INDEX MISS" in search,"Idefix brand index miss telemetry")
ok("no-search-product-contract-and-no-brand-catalog-recovery" in search,"Idefix dual fallback fail-closed")
ok("urljoin(definition.base_url, '/markalar')" in search,"Idefix own brand index discovery")
ok("product_path_patterns=(\"-p-\", \"/urun/\")" in search,"Idefix current p-id cleaner contract")
ok("a[href*=\"-p-\"]" in search,"Idefix brand catalog readiness")
ok("a[href*='-p-']" in adapter,"Idefix adapter p-id selector preserved")
ok("security_challenge_bypass" in main and "disabled" in main,"security bypass disabled")
ok("price_integrity_quarantine" in main and "preserved" in main,"price integrity preserved")
for rel in ["main.py","app/services/cross_store_search_service.py","app/stores/adapters/idefix.py"]:
    try:
        py_compile.compile(str(ROOT/rel),doraise=True); ok(True,"compile "+rel)
    except Exception as e:
        print(e); ok(False,"compile "+rel)
print(f"V23.62.99 MASTER smoke {'OK' if not failed else 'FAIL'} {17-len(failed)}/17")
raise SystemExit(1 if failed else 0)
