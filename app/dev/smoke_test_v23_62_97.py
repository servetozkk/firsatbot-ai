from pathlib import Path
import re, sqlite3, py_compile
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,name):
    checks.append((name,bool(cond))); print(('OK   ' if cond else 'FAIL ')+name)
main=(ROOT/'main.py').read_text(encoding='utf-8',errors='ignore')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8',errors='ignore')
adapter=(ROOT/'app/stores/adapters/idefix.py').read_text(encoding='utf-8',errors='ignore')
ok((ROOT/'VERSION').read_text().strip()=='23.62.97','VERSION 23.62.97')
ok('_RUNTIME_VERSION_V236297 = "23.62.97"' in main,'single runtime v236297')
ok('/api/runtime-identity/v236297' in main,'runtime endpoint v236297')
ok('/api/runtime-soak-stability/v236297' in main,'soak endpoint v236297')
ok('"runtime_version": _RUNTIME_VERSION_V236297' in main,'force response v236297')
ok("a[href*='-p-']" in adapter,'Idefix root product slug selector')
ok(r'-p-\d+' in adapter,'Idefix p-id extraction regex')
ok('a[href*="-p-"]' in search,'Idefix current slug readiness probe')
ok('V23.62.97 IDEFIX CURRENT-SLUG ANCHOR PROBE' in search,'Idefix v97 telemetry')
ok('V23.62.96 IDEFIX CANONICAL-STRONG-QUERY-ONLY' in search,'Idefix strong query preserved')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
fixture='https://www.idefix.com/xiaomi-redmi-note-15-pro-256-gb-8-gb-ram-titanyum-gri-xiaomi-turkiye-garantili-p-18925396'
pat=re.compile(r"https?://(?:www\.)?idefix\.com/[^\"'<>\s]+-p-\d+(?:\?[^\"'<>\s]*)?")
ok(bool(pat.search(fixture)),'current Idefix root slug fixture matched')
for rel in ['main.py','app/stores/adapters/idefix.py','app/services/cross_store_search_service.py']:
    try: py_compile.compile(str(ROOT/rel),doraise=True); good=True
    except Exception as e: print(e); good=False
    ok(good,'compile '+rel)
con=sqlite3.connect(ROOT/'data/products.db'); q=con.execute('PRAGMA quick_check').fetchone()[0]; con.close(); ok(q=='ok','packaged DB quick_check')
failed=[n for n,v in checks if not v]
print(f"V23.62.97 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
