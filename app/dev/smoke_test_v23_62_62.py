from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
generic=(ROOT/'app/scrapers/generic_store.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(ROOT/'VERSION').read_text().strip()=='23.62.62'),
 ('runtime v236262','/api/runtime-identity/v236262' in main),
 ('soak v236262','/api/runtime-soak-stability/v236262' in main),
 ('single source v236262','_RUNTIME_VERSION_V236262 = "23.62.62"' in main),
 ('force uses v236262','"runtime_version": _RUNTIME_VERSION_V236262' in main),
 ('recent detail cache','_N11_RECENT_VERIFIED_DETAIL_V236262' in repair),
 ('cache lock','_N11_RECENT_VERIFIED_DETAIL_LOCK_V236262' in repair),
 ('cache ttl 1800','_N11_RECENT_VERIFIED_DETAIL_TTL_SECONDS_V236262 = 1800.0' in repair),
 ('cache after canonical match','_v236262_n11_mark_recent_verified_detail' in repair),
 ('cache write after post color gate', repair.rfind('_v236262_n11_mark_recent_verified_detail(') > repair.find('V23.36 POST-SCRAPE COLOR GATE')),
 ('trust bridge marker','V23.62.62 N11 RECENT DETAIL TRUST BRIDGE' in repair),
 ('same global parameter','target_global_product_id=self.target_global_product_id' in repair),
 ('strict score 300','int(evidence.get("score") or 0) < 300' in repair),
 ('single price preserved','len(prices) != 1' in repair),
 ('exact family preserved','source_family.group(1) != candidate_family.group(1)' in repair),
 ('brand preserved','brand and brand not in candidate_text' in repair),
 ('accessory reject preserved','accessory_markers = (' in repair),
 ('v2350 recovery preserved','V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
 ('v2353 wiring preserved','V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
 ('v2361 inclusion preserved','V23.62.61 N11 DEDICATED-LANE INCLUSION INVARIANT' in cross),
 ('process shared session preserved','V23.62.60 N11 DETAIL HTTP CONNECTION' in generic),
 ('n11 detail 4.5 preserved','request_timeout_v23627 = 4.5' in generic),
 ('security bypass disabled','security_challenge_bypass' in main and '"disabled"' in main),
 ('price integrity preserved','price_integrity_quarantine' in main),
 ('production unchanged','production_ingestion_behavior' in main),
]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
if not all(ok for _,ok in checks): raise SystemExit(1)
print(f'V23.62.62 smoke OK {len(checks)}/{len(checks)}')
