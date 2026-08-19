from pathlib import Path
import ast, py_compile, sqlite3, sys
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(c,n): checks.append((bool(c),n)); print(("OK   " if c else "FAIL ")+n)
main=(ROOT/"main.py").read_text(encoding="utf-8")
repair=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
search=(ROOT/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
ok((ROOT/"VERSION").read_text(encoding="utf-8").strip()=="23.62.88","VERSION 23.62.88")
ok("_RUNTIME_VERSION_V236288 = \"23.62.88\"" in main,"single runtime v236288")
ok("/api/runtime-identity/v236288" in main,"runtime endpoint v236288")
ok("/api/runtime-soak-stability/v236288" in main,"soak endpoint v236288")
tree=ast.parse(main); force_src=""
for node in tree.body:
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name=="force_deep_refresh_v23629":
        force_src=ast.get_source_segment(main,node) or ""; break
ok(bool(force_src) and "\"runtime_version\": _RUNTIME_VERSION_V236288" in force_src,"REAL force response v236288")
ok("_RUNTIME_VERSION_V236287" not in force_src,"no stale v236287 inside force function")
ok("V23.62.88 AMAZON PHONE RECALL-SAFE PREFILTER" in repair,"recall-safe prefilter telemetry")
ok("explicit-accessory-card" in repair,"explicit accessory only hard reject")
ok('"uyumlu",' not in repair[repair.find("accessory_tokens_v236278"):repair.find("kept_v236278")],"generic uyumlu removed from hard tokens")
ok("V23.62.88 AMAZON PHONE LOW-PRICE SOFT SIGNAL" in repair,"low-price soft signal")
ok("retained_for_title_preflight=True" in repair,"low-price retained")
ok("V23.62.88 AMAZON PHONE PLAUSIBLE-PRICE PRIORITY" in search,"plausible-price priority telemetry")
ok("source_price_v236288 * 0.45" in search and "source_price_v236288 * 1.75" in search,"plausible price band")
ok("min(8, self.candidate_limit)" in search,"top8 preflight preserved")
ok("family:{source_family}!={detail_family}" in repair,"family gate preserved")
ok("storage:{source_storage}!={detail_storage}" in repair,"storage gate preserved")
ok('security_challenge_bypass": "disabled"' in main,"security bypass disabled")
ok('price_integrity_quarantine": "preserved"' in main,"price integrity preserved")
con=sqlite3.connect(ROOT/"data/products.db"); status=con.execute("PRAGMA integrity_check").fetchone()[0]; con.close(); ok(status=="ok","packaged DB integrity")
bad=[]; count=0
for f in ROOT.rglob("*.py"):
    count+=1
    try: py_compile.compile(str(f),doraise=True)
    except Exception as e: bad.append((str(f),str(e)))
ok(not bad,f"all Python syntax ({count} files)")
failed=[n for c,n in checks if not c]
print(f"V23.62.88 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed: print("FAILED:",failed); sys.exit(1)
