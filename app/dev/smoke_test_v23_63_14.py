from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.14',(ROOT/'VERSION').read_text().strip()=='23.63.14'),
 ('VERSION.txt 23.63.14',(ROOT/'VERSION.txt').read_text().strip()=='23.63.14'),
 ('runtime constant v236314','_RUNTIME_VERSION_V236314 = "23.63.14"' in main),
 ('runtime endpoint v236314','/api/runtime-identity/v236314' in main),
 ('soak endpoint v236314','/api/runtime-soak-stability/v236314' in main),
 ('force response exact v236314','"runtime_version": _RUNTIME_VERSION_V236314,\n            "test_only": True' in main),
 ('stale force v236309 removed','"runtime_version": _RUNTIME_VERSION_V236309,\n            "test_only": True' not in main),
 ('PttAVM seller-brand repair preserved','V23.63.10 PTTAVM SELLER-AS-BRAND REPAIR' in (ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')),
 ('Beymen preserved','beymen' in main.lower()),
 ('force budget 14','"force_store_budget": 14' in main),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','\"price_integrity_quarantine\": \"preserved\"' in main),
 ('Turkcell iOS direct discovery','V23.63.12 TURKCELL PASAJ IOS DIRECT PHONE DISCOVERY' in (ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')),
 ('Turkcell iPhone path contract','ios-telefonlar/{apple_group}' in (ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')),
 ('Turkcell Android discovery preserved','V23.63.01 TURKCELL PASAJ DIRECT PHONE DISCOVERY' in (ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')),
 ('Turkcell iOS canonical candidate helper','_v236314_turkcell_ios_authoritative_match_candidate' in (ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')),
 ('Turkcell iOS canonical override telemetry','V23.63.14 TURKCELL IOS CANONICAL CANDIDATE IDENTITY OVERRIDE' in (ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')),
 ('Turkcell iOS matcher strips sibling specs','match_candidate.specifications = {}' in (ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')),
]
for rel in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/scraper_registry.py','app/scrapers/registry.py']:
    ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append((f'AST {rel}',True))
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('V23.63.14 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.14 MASTER smoke OK {len(checks)}/{len(checks)}')
