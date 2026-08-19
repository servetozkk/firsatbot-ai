from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.17',(ROOT/'VERSION').read_text().strip()=='23.63.17'),
 ('VERSION.txt 23.63.17',(ROOT/'VERSION.txt').read_text().strip()=='23.63.17'),
 ('runtime constant v236317','_RUNTIME_VERSION_V236317 = "23.63.17"' in main),
 ('runtime endpoint v236317','/api/runtime-identity/v236317' in main),
 ('soak endpoint v236317','/api/runtime-soak-stability/v236317' in main),
 ('force response exact v236317','"runtime_version": _RUNTIME_VERSION_V236317,\n            "test_only": True' in main),
 ('Idefix curated recovery telemetry','V23.63.17 IDEFIX APPLE IPHONE CURATED-LANDING RECOVERY' in cross),
 ('Idefix curated official path',"/iphone-modellerini-kesfedin-l-21049" in cross),
 ('Idefix scope Apple only','brand_slug_v236299 == "apple"' in cross),
 ('Idefix scope iPhone only','"iphone" in source_identity_text_v236317' in cross),
 ('Idefix normal gate preservation telemetry','normal_match_gates_preserved=True' in cross),
 ('Idefix v23.63.00 general recovery preserved','V23.62.99 IDEFIX BRAND-CATALOG RECOVERY' in cross),
 ('HB v23.63.16 retry preserved','V23.63.16 HEPSIBURADA TRANSIENT HTTP2 NAVIGATION RETRY' in cross),
 ('PttAVM v23.63.15 retry preserved','V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY' in cross),
 ('PttAVM seller-brand repair preserved','V23.63.10 PTTAVM SELLER-AS-BRAND REPAIR' in (ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')),
 ('Turkcell v23.63.14 preserved','V23.63.14 TURKCELL IOS CANONICAL CANDIDATE IDENTITY OVERRIDE' in repair),
 ('Turkcell sibling strip preserved','match_candidate.specifications = {}' in repair),
 ('force budget 14','"force_store_budget": 14' in main),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py','app/services/scraper_registry.py','app/scrapers/registry.py','app/stores/adapters/idefix.py']:
    ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append((f'AST {rel}',True))
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('V23.63.17 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.17 MASTER smoke OK {len(checks)}/{len(checks)}')
