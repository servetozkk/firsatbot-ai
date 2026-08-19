from pathlib import Path
import ast
import sqlite3
import subprocess
import sys
import tempfile
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,name):
    checks.append((name,bool(cond))); print(("OK   " if cond else "FAIL ")+name)

version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
main=(ROOT/'main.py').read_text(encoding='utf-8')
cont=(ROOT/'app/ops/data_continuity_v236284.py').read_text(encoding='utf-8')
integ=(ROOT/'app/ops/database_integrity_v23616.py').read_text(encoding='utf-8')
launcher=(ROOT/'BASLAT.bat').read_text(encoding='utf-8')
ok(version=='23.62.85','VERSION 23.62.85')
ok('_RUNTIME_VERSION_V236285 = "23.62.85"' in main,'single runtime v236285')
ok('/api/runtime-identity/v236285' in main,'runtime endpoint v236285')
ok('/api/runtime-soak-stability/v236285' in main,'soak endpoint v236285')
ok('"runtime_version": _RUNTIME_VERSION_V236285' in main,'force response v236285')
ok('src.backup(dst)' in cont,'SQLite backup API')
ok('PRAGMA integrity_check' in cont,'full integrity gate')
ok('_select_best_candidate' in cont,'coverage-aware continuity selector')
ok('active + offers' in cont and '0.95' in cont,'offer-rich 95pct coverage policy')
ok('sys.path.insert(0, str(ROOT))' in integ,'direct-run integrity import bootstrap')
ok('python -m app.ops.startup_preflight_v236284' in launcher,'module startup preflight')
ok('python -m app.ops.data_continuity_v236284' in launcher,'module continuity launcher')
ok('python -m app.ops.database_integrity_v23616' in launcher,'module integrity launcher')
ok('smoke_test_v23_62_85.py' in launcher,'current smoke launcher')
ok('set "PYTHONPATH=%CD%;%PYTHONPATH%"' in launcher,'launcher PYTHONPATH root')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
# Selection regression: 163 products + 265 offers must beat 169 + 249 when within 95% coverage.
spec=importlib.util.spec_from_file_location('cont_v236284', ROOT/'app/ops/data_continuity_v236284.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
a={'valid':True,'path':'FirsatAI-v23.31/data/products.db','global_products':169,'active_global_offers':225,'global_offers':249,'global_price_history':0,'product_offers':0,'raw_products':0,'has_143':1,'favorites':0,'price_history':0,'size':1,'mtime':1}
b={'valid':True,'path':'FirsatAI-v23.62.82/data/products.db','global_products':163,'active_global_offers':224,'global_offers':265,'global_price_history':0,'product_offers':0,'raw_products':0,'has_143':1,'favorites':0,'price_history':0,'size':1,'mtime':1}
selected=mod._select_best_candidate([a,b])
ok(selected is b,'offer-rich v82 beats older +6 product / -16 offer DB')
# Packaged seed DB health.
db=ROOT/'data/products.db'
try:
    con=sqlite3.connect(str(db)); verdict=con.execute('PRAGMA integrity_check').fetchone()[0]; con.close()
    ok(str(verdict).lower()=='ok','packaged DB integrity')
except Exception:
    ok(False,'packaged DB integrity')
# Direct execution import regression from project root.
proc=subprocess.run([sys.executable, str(ROOT/'app/ops/database_integrity_v23616.py')], cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
ok(proc.returncode==0,'database integrity direct execution')
if proc.returncode!=0:
    print(proc.stdout); print(proc.stderr)
# Parse all Python sources.
bad=[]
for src in ROOT.rglob('*.py'):
    try: ast.parse(src.read_text(encoding='utf-8-sig'), filename=str(src))
    except Exception as exc: bad.append((src,exc))
ok(not bad,f'all Python syntax ({len(list(ROOT.rglob("*.py")))} files)')
if bad:
    for src,e in bad[:20]: print('  ',src,e)
failed=[n for n,v in checks if not v]
print(f"V23.62.85 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
