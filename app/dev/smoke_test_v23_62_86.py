from pathlib import Path
import ast
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
main_path = ROOT / "main.py"
svc_path = ROOT / "app" / "services" / "multi_store_offer_repair_v14_service.py"
main = main_path.read_text(encoding="utf-8")
svc = svc_path.read_text(encoding="utf-8")
failed=[]
checks=[]
def ok(cond,label):
    checks.append(label)
    if cond: print("OK  ",label)
    else:
        print("FAIL",label); failed.append(label)

ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='23.62.86','VERSION 23.62.86')
ok('_RUNTIME_VERSION_V236286 = "23.62.86"' in main,'single runtime v236286')
ok('/api/runtime-identity/v236286' in main,'runtime endpoint v236286')
ok('/api/runtime-soak-stability/v236286' in main,'soak endpoint v236286')
# AST-check the actual force function return, not a global string occurrence.
tree=ast.parse(main)
force_node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='force_deep_refresh_v23629')
force_src=ast.get_source_segment(main,force_node) or ''
ok('"runtime_version": _RUNTIME_VERSION_V236286' in force_src,'REAL force response v236286')
ok('_RUNTIME_VERSION_V236284' not in force_src,'no stale v236284 inside force function')
ok('len(candidate_urls) > 8' in svc and 'candidate_urls = candidate_urls[:8]' in svc,'Amazon preflight top8 cap')
ok('pro\\s*\\+(?=\\s|$|[^a-z0-9])' in svc,'Pro+ regex boundary fix')
# Execute helper without importing application side effects.
module=ast.parse(svc)
funcs={n.name:n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'_v236283_fold','_v236283_phone_variant_signature'}}
mini=ast.Module(body=[ast.Import(names=[ast.alias('re')]),ast.Import(names=[ast.alias('unicodedata')])]+[funcs['_v236283_fold'],funcs['_v236283_phone_variant_signature']],type_ignores=[])
ns={}; exec(compile(ast.fix_missing_locations(mini),'<variant-test>','exec'),ns)
sig=ns['_v236283_phone_variant_signature']
ok(sig('REDMI Note 15 Pro+ 5G 8GB+256GB Black')==('pro_plus',),'Pro+ stays distinct')
ok(sig('Redmi Note 15 Pro 8GB 256GB')==('pro',),'plain Pro stays Pro')
ok(sig('Redmi Note 15 8GB 256GB')==(), 'base phone has no Pro tier')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
# packaged DB integrity
con=sqlite3.connect(str(ROOT/'data'/'products.db')); val=con.execute('PRAGMA integrity_check').fetchone()[0]; con.close()
ok(val=='ok','packaged DB integrity')
# all python syntax
count=0
for py in ROOT.rglob('*.py'):
    try: compile(py.read_text(encoding='utf-8'),str(py),'exec'); count+=1
    except UnicodeDecodeError: compile(py.read_text(encoding='utf-8-sig'),str(py),'exec'); count+=1
    except Exception as e: print('SYNTAX FAIL',py,e); failed.append('all Python syntax'); break
else: print(f'OK   all Python syntax ({count} files)'); checks.append('all Python syntax')
print(f"V23.62.86 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
sys.exit(1 if failed else 0)
