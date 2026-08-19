from pathlib import Path
import ast, sqlite3
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8',errors='ignore')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8',errors='ignore')
reg=(ROOT/'app/scrapers/registry.py').read_text(encoding='utf-8',errors='ignore')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8',errors='ignore')
adreg=(ROOT/'app/stores/adapters/registry.py').read_text(encoding='utf-8',errors='ignore')
norm=(ROOT/'app/services/normalization_service.py').read_text(encoding='utf-8',errors='ignore')
checks=[
 ('VERSION 23.63.01',(ROOT/'VERSION').read_text().strip()=='23.63.01'),
 ('runtime endpoint v236301','/api/runtime-identity/v236301' in main),
 ('force runtime v236301','"runtime_version": _RUNTIME_VERSION_V236301' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]),
 ('Turkcell search definition','code="turkcellpasaj"' in cross and 'Turkcell Pasaj' in cross),
 ('Turkcell priority','"turkcellpasaj": 89' in cross),
 ('Turkcell direct phone discovery','V23.63.01 TURKCELL PASAJ DIRECT PHONE DISCOVERY' in cross),
 ('Turkcell adapter registered','TURKCELL_PASAJ_ADAPTER.code' in adreg),
 ('Turkcell scraper config','"turkcellpasaj": GenericStoreConfig' in retail),
 ('Turkcell scraper registered','code="turkcellpasaj"' in reg and 'TurkcellPasajScraper' in reg),
 ('Turkcell normalization alias','"turkcell com tr": "turkcellpasaj"' in norm),
 ('Amazon v91 preserved','v23.62.91-preserved' in main),
 ('N11 v95 preserved','v23.62.95-preserved' in main),
 ('Idefix v99 preserved','v23.62.99-preserved' in main),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/services/cross_store_search_service.py','app/scrapers/registry.py','app/scrapers/retail_stores.py','app/stores/adapters/turkcellpasaj.py','app/stores/adapters/registry.py']:
    ast.parse((ROOT/rel).read_text(encoding='utf-8',errors='ignore'))
checks.append(('critical Python AST',True))
db=ROOT/'data/products.db'
if db.exists():
    con=sqlite3.connect(str(db)); qc=con.execute('PRAGMA quick_check').fetchone()[0]; con.close()
    checks.append(('packaged DB quick_check',qc=='ok'))
failed=[]
for name,ok in checks:
    print(('OK  ' if ok else 'FAIL'),name)
    if not ok: failed.append(name)
if failed: raise SystemExit('FAILED: '+', '.join(failed))
print(f'V23.63.01 MASTER smoke OK {len(checks)}/{len(checks)}')
