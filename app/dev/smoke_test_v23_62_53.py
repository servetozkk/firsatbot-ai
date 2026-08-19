from pathlib import Path

root=Path(__file__).resolve().parents[2]
version=(root/'VERSION').read_text(encoding='utf-8').strip()
main=(root/'main.py').read_text(encoding='utf-8')
repair=(root/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
cross=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')

checks=[
 ('VERSION',version=='23.62.53'),
 ('runtime v236253','/api/runtime-identity/v236253' in main),
 ('soak v236253','/api/runtime-soak-stability/v236253' in main),
 ('single source','_RUNTIME_VERSION_V236253 = "23.62.53"' in main),
 ('force uses v236253','"runtime_version": _RUNTIME_VERSION_V236253' in main),
 ('wiring marker','V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
 ('n11 challenge recorded','errors.append("SECURITY_CHALLENGE")' in repair),
 ('n11 challenge continues','if definition.code == "n11":' in repair and 'continue\n                return StoreScanResult' in repair),
 ('other stores fail closed','message="SECURITY_CHALLENGE"' in repair),
 ('v2350 recovery preserved','V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
 ('recovery post exhaustion preserved','for recovery_url_v236250 in candidate_urls:' in repair),
 ('strong first 4500 preserved','(4_500 if n11_strong_first_budget_v236234 else 4_500)' in cross),
 ('base probe 350 preserved','timeout=350' in cross),
 ('near miss retired','V23.62.51 N11 NEAR-MISS SELECTOR RECOVERY' not in cross),
 ('detail 4.5 preserved','request_timeout_v23627 = 4.5' in (root/'app/scrapers/generic_store.py').read_text(encoding='utf-8')),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
 ('production unchanged','"production_ingestion_behavior": "unchanged"' in main),
]
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed:
 raise SystemExit('FAILED: '+', '.join(failed))
print(f'V23.62.53 smoke OK {len(checks)}/{len(checks)}')
