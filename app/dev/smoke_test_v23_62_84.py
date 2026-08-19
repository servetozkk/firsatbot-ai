from pathlib import Path
import ast, sqlite3
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,name):
    checks.append((name,bool(cond))); print(("OK   " if cond else "FAIL ")+name)
version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
main=(ROOT/'main.py').read_text(encoding='utf-8')
cont=(ROOT/'app/ops/data_continuity_v236284.py').read_text(encoding='utf-8')
launcher=(ROOT/'BASLAT.bat').read_text(encoding='utf-8')
ok(version=='23.62.84','VERSION 23.62.84')
ok('_RUNTIME_VERSION_V236284 = "23.62.84"' in main,'single runtime v236284')
ok('/api/runtime-identity/v236284' in main,'runtime endpoint v236284')
ok('/api/runtime-soak-stability/v236284' in main,'soak endpoint v236284')
ok('"runtime_version": _RUNTIME_VERSION_V236284' in main,'force response v236284')
ok('Path.home()/"Desktop"' in cont and 'Path.home()/"Downloads"' in cont,'user-profile DB discovery')
ok('src.backup(dst)' in cont,'SQLite backup API')
ok('PRAGMA integrity_check' in cont,'full integrity gate')
ok('global_products' in cont and 'has_143' in cont,'coverage-aware continuity score')
ok('startup_preflight_v236284.py' in launcher,'port safety preflight')
ok('data_continuity_v236284.py' in launcher,'WAL-safe continuity launcher')
ok('smoke_test_v23_62_84.py' in launcher,'current smoke launcher')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
# Packaged seed DB must itself be healthy even if user continuity later replaces it.
db=ROOT/'data/products.db'
try:
    con=sqlite3.connect(str(db)); verdict=con.execute('PRAGMA integrity_check').fetchone()[0]; con.close()
    ok(str(verdict).lower()=='ok','packaged DB integrity')
except Exception:
    ok(False,'packaged DB integrity')
# Parse all Python sources to catch syntax regressions without importing optional deps.
bad=[]
for p in ROOT.rglob('*.py'):
    try: ast.parse(p.read_text(encoding='utf-8-sig'), filename=str(p))
    except Exception as exc: bad.append((p,exc))
ok(not bad,f'all Python syntax ({len(list(ROOT.rglob("*.py")))} files)')
if bad:
    for p,e in bad[:20]: print('  ',p,e)
failed=[n for n,v in checks if not v]
print(f"V23.62.84 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
