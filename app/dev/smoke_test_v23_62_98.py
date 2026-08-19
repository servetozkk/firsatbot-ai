from pathlib import Path
import py_compile, sqlite3, sys
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(c,m):
    checks.append((bool(c),m)); print(('OK   ' if c else 'FAIL ')+m)
main=(ROOT/'main.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
adapter=(ROOT/'app/stores/adapters/idefix.py').read_text(encoding='utf-8')
ok((ROOT/'VERSION').read_text().strip()=='23.62.98','VERSION 23.62.98')
ok('_RUNTIME_VERSION_V236298 = "23.62.98"' in main,'single runtime v236298')
ok('/api/runtime-identity/v236298' in main,'runtime endpoint v236298')
ok('/api/runtime-soak-stability/v236298' in main,'soak endpoint v236298')
ok('"runtime_version": _RUNTIME_VERSION_V236298' in main,'force response v236298')
ok('V23.62.98 IDEFIX ANCHOR-OR-HTML CONTRACT' in search,'Idefix anchor-or-html telemetry')
ok('V23.62.98 IDEFIX HTML-CONTRACT RECOVERY' in search,'Idefix html-contract recovery telemetry')
ok('no-product-anchor-or-html-product-contract' in search,'Idefix dual evidence fail-closed')
ok('html_candidates(' in search,'Idefix page HTML adapter contract probe')
ok("a[href*='-p-']" in adapter,'Idefix current root slug selector preserved')
ok('-p-\\d+' in adapter,'Idefix p-id extraction regex preserved')
ok('security_challenge_bypass' in main and '"disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine' in main and '"preserved"' in main,'price integrity preserved')
for f in [ROOT/'main.py',ROOT/'app/services/cross_store_search_service.py',ROOT/'app/stores/adapters/idefix.py']:
    try: py_compile.compile(str(f),doraise=True); ok(True,'compile '+str(f.relative_to(ROOT)))
    except Exception as e: ok(False,'compile '+str(f.relative_to(ROOT))+' '+str(e))
# adapter fixture
sys.path.insert(0,str(ROOT))
from app.stores.adapters.idefix import IDEFIX_ADAPTER
fixture='<script>window.x={"url":"/xiaomi-redmi-note-15-pro-256-gb-8-gb-ram-titanyum-gri-xiaomi-turkiye-garantili-p-18925396"}</script>'
cands=IDEFIX_ADAPTER.html_candidates(fixture,'https://www.idefix.com')
ok(any('p-18925396' in str(x.get('href','')) for x in cands),'Idefix embedded-html root slug fixture matched')
db=ROOT/'data/products.db'
try:
    con=sqlite3.connect('file:'+str(db).replace('\\','/')+'?mode=ro',uri=True)
    qc=con.execute('PRAGMA quick_check').fetchone()[0]; con.close(); ok(qc=='ok','packaged DB quick_check')
except Exception as e: ok(False,'packaged DB quick_check '+str(e))
failed=[m for c,m in checks if not c]
print(f"V23.62.98 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
