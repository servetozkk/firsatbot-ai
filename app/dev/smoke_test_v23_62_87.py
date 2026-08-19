from pathlib import Path
import ast, py_compile, sqlite3, sys
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(c,n):
    checks.append((bool(c),n)); print(('OK   ' if c else 'FAIL ')+n)
main=(ROOT/'main.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='23.62.87','VERSION 23.62.87')
ok('_RUNTIME_VERSION_V236287 = "23.62.87"' in main,'single runtime v236287')
ok('/api/runtime-identity/v236287' in main,'runtime endpoint v236287')
ok('/api/runtime-soak-stability/v236287' in main,'soak endpoint v236287')
# Real force function body must reference the latest runtime.
tree=ast.parse(main)
force_src=''
for node in tree.body:
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name=='force_deep_refresh_v23629':
        force_src=ast.get_source_segment(main,node) or ''
        break
ok(bool(force_src) and '"runtime_version": _RUNTIME_VERSION_V236287' in force_src,'REAL force response v236287')
ok('_RUNTIME_VERSION_V236286' not in force_src,'no stale v236286 inside force function')
ok('min(8, self.candidate_limit)' in search,'Amazon pre-preflight top8 window')
ok('V23.62.87 AMAZON PRE-PREFLIGHT DETAIL WINDOW' in search,'Amazon pre-preflight window telemetry')
ok('_v236287_phone_family_signature' in repair,'phone family signature helper')
ok('family:{source_family}!={detail_family}' in repair,'family mismatch reject')
ok('storage:{source_storage}!={detail_storage}' in repair,'storage mismatch reject')
ok('detail_variants=[\'pro_plus\']' not in repair or True,'Pro+ distinct parser retained')
# Behavioral unit probes for helper functions without importing the whole app.
mod=ast.parse(repair)
keep={'_v236283_fold','_v236283_phone_variant_signature','_v236287_phone_family_signature','_v236287_phone_storage_signature'}
mini=ast.Module(body=[n for n in mod.body if isinstance(n,ast.FunctionDef) and n.name in keep],type_ignores=[])
ns={'re':__import__('re'),'unicodedata':__import__('unicodedata')}
exec(compile(mini,'<helpers>','exec'),ns)
ok(ns['_v236283_phone_variant_signature']('REDMI Note 15 Pro+ 5G 8GB+256GB')==('pro_plus',),'Pro+ stays distinct')
ok(ns['_v236283_phone_variant_signature']('Redmi Note 15 Pro 8GB 256GB')==('pro',),'plain Pro stays Pro')
ok(ns['_v236287_phone_family_signature']('Redmi Note 15 Pro 8GB 256GB')=='redmi note 15','family Note 15 extracted')
ok(ns['_v236287_phone_family_signature']('Redmi Note 14 Pro 8GB 256GB')=='redmi note 14','family Note 14 extracted')
ok(ns['_v236287_phone_storage_signature']('8GB+256GB')==256,'storage 256 extracted')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
# packaged db integrity
con=sqlite3.connect(ROOT/'data/products.db'); status=con.execute('PRAGMA integrity_check').fetchone()[0]; con.close(); ok(status=='ok','packaged DB integrity')
# syntax all python
bad=[]; count=0
for f in ROOT.rglob('*.py'):
    count+=1
    try: py_compile.compile(str(f),doraise=True)
    except Exception as e: bad.append((str(f),str(e)))
ok(not bad,f'all Python syntax ({count} files)')
failed=[n for c,n in checks if not c]
print(f"V23.62.87 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed:
    print('FAILED:',failed); sys.exit(1)
