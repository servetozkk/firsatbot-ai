from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.15',(ROOT/'VERSION').read_text().strip()=='23.63.15'),
 ('VERSION.txt 23.63.15',(ROOT/'VERSION.txt').read_text().strip()=='23.63.15'),
 ('runtime constant v236315','_RUNTIME_VERSION_V236315 = "23.63.15"' in main),
 ('runtime endpoint v236315','/api/runtime-identity/v236315' in main),
 ('soak endpoint v236315','/api/runtime-soak-stability/v236315' in main),
 ('force response exact v236315','"runtime_version": _RUNTIME_VERSION_V236315,\n            "test_only": True' in main),
 ('PttAVM retry scope','definition.code == "pttavm"' in cross and 'ERR_HTTP_RESPONSE_CODE_FAILURE' in cross),
 ('PttAVM single retry telemetry','V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY' in cross),
 ('PttAVM exhausted fail closed','V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY EXHAUSTED' in cross and 'fail_closed=True' in cross),
 ('PttAVM seller-brand repair preserved','V23.63.10 PTTAVM SELLER-AS-BRAND REPAIR' in (ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')),
 ('Turkcell v23.63.14 preserved','V23.63.14 TURKCELL IOS CANONICAL CANDIDATE IDENTITY OVERRIDE' in repair),
 ('Turkcell sibling strip preserved','match_candidate.specifications = {}' in repair),
 ('force budget 14','"force_store_budget": 14' in main),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py','app/services/scraper_registry.py','app/scrapers/registry.py']:
    ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append((f'AST {rel}',True))
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('V23.63.15 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.15 MASTER smoke OK {len(checks)}/{len(checks)}')
