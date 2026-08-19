from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.11',(ROOT/'VERSION').read_text().strip()=='23.63.11'),
 ('VERSION.txt 23.63.11',(ROOT/'VERSION.txt').read_text().strip()=='23.63.11'),
 ('runtime constant v236311','_RUNTIME_VERSION_V236311 = "23.63.11"' in main),
 ('runtime endpoint v236311','/api/runtime-identity/v236311' in main),
 ('soak endpoint v236311','/api/runtime-soak-stability/v236311' in main),
 ('force response exact v236311','"runtime_version": _RUNTIME_VERSION_V236311,\n            "test_only": True' in main),
 ('stale force v236309 removed','"runtime_version": _RUNTIME_VERSION_V236309,\n            "test_only": True' not in main),
 ('PttAVM seller-brand repair preserved','V23.63.10 PTTAVM SELLER-AS-BRAND REPAIR' in (ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')),
 ('Beymen preserved','beymen' in main.lower()),
 ('force budget 14','"force_store_budget": 14' in main),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/scraper_registry.py','app/scrapers/registry.py']:
    ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append((f'AST {rel}',True))
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('V23.63.11 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.11 MASTER smoke OK {len(checks)}/{len(checks)}')
