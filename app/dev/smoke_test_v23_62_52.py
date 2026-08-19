from pathlib import Path
root=Path(__file__).resolve().parents[2]
main=(root/'main.py').read_text(encoding='utf-8')
cross=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(root/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
version=(root/'VERSION').read_text(encoding='utf-8').strip()
checks=[
 ('VERSION',version=='23.62.52'),
 ('runtime v236252','/api/runtime-identity/v236252' in main),
 ('soak v236252','/api/runtime-soak-stability/v236252' in main),
 ('single source','_RUNTIME_VERSION_V236252 = "23.62.52"' in main),
 ('force uses v236252','"runtime_version": _RUNTIME_VERSION_V236252' in main),
 ('4500 consolidation marker','V23.62.52 N11 STRONG-FIRST 4500MS CONSOLIDATION' in cross),
 ('strong first 4500','4_500 if n11_strong_first_budget_v236234 else 4_500' in cross),
 ('base probe 350','timeout=350' in cross),
 ('near miss code retired','V23.62.51 N11 NEAR-MISS SELECTOR RECOVERY' not in cross),
 ('extra probe 450 retired','timeout=450' not in cross),
 ('runtime says near miss retired','"n11_near_miss_extra_selector_probe": "retired-v23.62.52"' in main),
 ('same DOM selector','page.locator("a[href*=\'/urun/\']").first.wait_for' in cross),
 ('normal gates preserved','adapter = StoreAdapterRegistry.get(definition.code)' in cross),
 ('v2350 recovery preserved','V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
 ('detail 4.5 preserved','"n11_detail_http_timeout_seconds": 4.5' in main),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
 ('production unchanged','"production_ingestion_behavior": "unchanged"' in main),
]
failed=[]
for name,ok in checks:
    print(('OK  ' if ok else 'FAIL ')+name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit('Smoke failed: '+', '.join(failed))
print(f'V23.62.52 smoke OK {len(checks)}/{len(checks)}')
