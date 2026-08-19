from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.16',(ROOT/'VERSION').read_text().strip()=='23.63.16'),
 ('VERSION.txt 23.63.16',(ROOT/'VERSION.txt').read_text().strip()=='23.63.16'),
 ('runtime constant v236316','_RUNTIME_VERSION_V236316 = "23.63.16"' in main),
 ('runtime endpoint v236316','/api/runtime-identity/v236316' in main),
 ('soak endpoint v236316','/api/runtime-soak-stability/v236316' in main),
 ('force response exact v236316','"runtime_version": _RUNTIME_VERSION_V236316,\n            "test_only": True' in main),
 ('HB retry exact store scope','definition.code == "hepsiburada"' in cross and 'ERR_HTTP2_PROTOCOL_ERROR' in cross),
 ('HB single retry telemetry','V23.63.16 HEPSIBURADA TRANSIENT HTTP2 NAVIGATION RETRY' in cross),
 ('HB exhausted fail closed','V23.63.16 HEPSIBURADA TRANSIENT HTTP2 NAVIGATION RETRY EXHAUSTED' in cross and 'fail_closed=True' in cross),
 ('HB retry preserves domcontentloaded','retry_wait_until_v236316 = "domcontentloaded"' in cross),
 ('security challenge bypass absent','hepsiburada_transient_http2_failure_v236316' in cross and 'SECURITY_CHALLENGE' not in cross[cross.find('hepsiburada_transient_http2_failure_v236316'):cross.find('hepsiburada_transient_http2_failure_v236316')+500]),
 ('PttAVM v23.63.15 retry preserved','V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY' in cross),
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
if failed: raise SystemExit('V23.63.16 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.16 MASTER smoke OK {len(checks)}/{len(checks)}')
