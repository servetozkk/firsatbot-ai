from pathlib import Path
import ast, sqlite3
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
svc=(ROOT/'app/services/scraper_registry.py').read_text(encoding='utf-8')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.02',(ROOT/'VERSION').read_text().strip()=='23.63.02'),
 ('runtime endpoint v236302','/api/runtime-identity/v236302' in main),
 ('force runtime v236302','"runtime_version": _RUNTIME_VERSION_V236302' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]),
 ('service registry Turkcell import','TurkcellPasajScraper' in svc.split('STORE_SCRAPER_DEFINITIONS')[0]),
 ('service registry Turkcell definition','code="turkcellpasaj"' in svc and 'domains=(\n            "turkcell.com.tr"' in svc),
 ('service registry Turkcell class','scraper_class=TurkcellPasajScraper' in svc),
 ('retail Turkcell config','"turkcellpasaj": GenericStoreConfig' in retail),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/services/scraper_registry.py','app/scrapers/registry.py','app/scrapers/retail_stores.py']:
    ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append((f'AST {rel}',True))
con=sqlite3.connect(ROOT/'data/products.db'); qc=con.execute('PRAGMA quick_check').fetchone()[0]; con.close(); checks.append(('packaged DB quick_check',qc=='ok'))
for n,ok in checks:
 print(('OK  ' if ok else 'FAIL'),n)
 if not ok: raise SystemExit(1)
print(f'V23.63.02 MASTER smoke OK {len(checks)}/{len(checks)}')
