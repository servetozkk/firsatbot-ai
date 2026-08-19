from pathlib import Path
root=Path(__file__).resolve().parents[2]
version=(root/'VERSION').read_text(encoding='utf-8').strip()
main=(root/'main.py').read_text(encoding='utf-8')
cross=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(root/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
('VERSION',version=='23.62.54'),
('runtime v236254','/api/runtime-identity/v236254' in main),
('soak v236254','/api/runtime-soak-stability/v236254' in main),
('single source','_RUNTIME_VERSION_V236254 = "23.62.54"' in main),
('force uses v236254','"runtime_version": _RUNTIME_VERSION_V236254' in main),
('telemetry metadata','v23.62.54-query-core-browser-cleanup-postprocess-find-total' in main),
('cleanup marker','V23.62.54 N11 SEARCH CLEANUP:' in cross),
('breakdown marker','V23.62.54 N11 SEARCH PHASE BREAKDOWN:' in cross),
('query core','query_core=' in cross),
('browser cleanup','browser_cleanup=' in cross),
('postprocess','postprocess=' in cross),
('unattributed','unattributed=' in cross),
('4500 preserved','4_500 if n11_strong_first_budget_v236234' in cross and 'V23.62.52 N11 STRONG-FIRST 4500MS CONSOLIDATION' in cross),
('350 preserved','350' in cross and 'N11 TIMEOUT SELECTOR RECOVERY' in cross),
('v2350 recovery preserved','V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
('v2353 wiring preserved','V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
('security bypass disabled','security_challenge_bypass": "disabled"' in main),
('price integrity preserved','price_integrity_quarantine": "preserved"' in main),
('production unchanged','production_ingestion_behavior": "unchanged"' in main),
]
bad=[n for n,ok in checks if not ok]
for n,ok in checks: print(('OK  ' if ok else 'FAIL ')+n)
if bad: raise SystemExit('FAILED: '+', '.join(bad))
print(f'V23.62.54 smoke OK {len(checks)}/{len(checks)}')
