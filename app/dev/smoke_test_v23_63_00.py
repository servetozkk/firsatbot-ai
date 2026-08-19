from pathlib import Path
import py_compile, sqlite3
ROOT=Path(__file__).resolve().parents[2]
failed=[]
def ok(c,m):
    print(('OK   ' if c else 'FAIL ')+m)
    if not c: failed.append(m)
main=(ROOT/'main.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
ok((ROOT/'VERSION').read_text().strip()=='23.63.00','VERSION 23.63.00')
ok('_RUNTIME_VERSION_V236300 = "23.63.00"' in main,'single runtime v236300')
ok('/api/runtime-identity/v236300' in main,'runtime endpoint v236300')
ok('/api/runtime-soak-stability/v236300' in main,'soak endpoint v236300')
ok('"runtime_version": _RUNTIME_VERSION_V236300' in main,'force response v236300')
ok('V23.62.99 IDEFIX BRAND-CATALOG RECOVERY' in search,'Idefix v99 brand recovery preserved')
ok('V23.63.00 IDEFIX POST-RECOVERY SEARCH PHASE' in search,'Idefix post-recovery telemetry')
ok('idefix_phase_elapsed_v236300 = perf_counter() - query_started_v23628' in search,'Idefix elapsed direct measurement')
ok('elapsed={query_elapsed_v23628:.3f}s' not in search[search.find('elif definition.code == "idefix":'):search.find('elif definition.code == "hepsiburada":', search.find('elif definition.code == "idefix":'))], 'no pre-assignment query_elapsed read in Idefix phase')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
for rel in ['main.py','app/services/cross_store_search_service.py','app/stores/adapters/idefix.py']:
    try: py_compile.compile(str(ROOT/rel), doraise=True); c=True
    except Exception as e: print(e); c=False
    ok(c,'compile '+rel)
try:
    con=sqlite3.connect(str(ROOT/'data/products.db')); qc=con.execute('pragma quick_check').fetchone()[0]; con.close()
    ok(qc=='ok','packaged DB quick_check')
except Exception as e:
    print(e); ok(False,'packaged DB quick_check')
print(f"V23.63.00 MASTER smoke {'OK' if not failed else 'FAIL'} {15-len(failed)}/15")
raise SystemExit(1 if failed else 0)
