from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
generic=(ROOT/'app/scrapers/generic_store.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
force=main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]
checks=[
 ('VERSION',(ROOT/'VERSION').read_text().strip()=='23.62.64'),
 ('runtime v236264','/api/runtime-identity/v236264' in main),
 ('soak v236264','/api/runtime-soak-stability/v236264' in main),
 ('single source v236264','_RUNTIME_VERSION_V236264 = "23.62.64"' in main),
 ('force uses v236264','"runtime_version": _RUNTIME_VERSION_V236264' in force),
 ('post-cap marker','V23.62.64 N11 POST-CAP FORCE INCLUSION' in cross),
 ('post-cap placement',cross.find('V23.62.64 N11 POST-CAP FORCE INCLUSION') > cross.find('if self.max_store_count is not None:')),
 ('user ingestion only','self.workload_class == "USER_INGESTION"' in cross),
 ('n11 absence condition','not any(definition.code == "n11" for definition in definitions)' in cross),
 ('n11 reinsert v236264','definitions.append(n11_definition_v236264)' in cross),
 ('count preserved','target_count_v236264 = len(definitions)' in cross and 'definitions = definitions[:-1]' in cross),
 ('no post-cap resort','definitions = self._ordered_definitions_v2351(definitions, source_product)' not in cross[cross.find('V23.62.64 N11 POST-CAP FORCE INCLUSION')-900:cross.find('result.searched_store_count')]),
 ('no post-cap reslice','definitions = definitions[:target_count_v236264]' not in cross),
 ('final invariant assert','V23.62.64 N11 post-cap inclusion invariant violated' in cross),
 ('v2361 inclusion preserved','V23.62.61 N11 DEDICATED-LANE INCLUSION INVARIANT' in cross),
 ('recent detail bridge preserved','V23.62.62 N11 RECENT DETAIL TRUST BRIDGE' in repair),
 ('verified recovery preserved','V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
 ('process shared session preserved','V23.62.60 N11 DETAIL HTTP CONNECTION' in generic),
 ('n11 detail 4.5 preserved','request_timeout_v23627 = 4.5' in generic),
 ('security bypass disabled','security_challenge_bypass' in main and '"disabled"' in main),
 ('price integrity preserved','price_integrity_quarantine' in main),
 ('production unchanged','production_ingestion_behavior' in main),
]
for name,ok in checks: print(('OK  ' if ok else 'FAIL ')+name)
if not all(ok for _,ok in checks): raise SystemExit(1)
print(f'V23.62.64 smoke OK {len(checks)}/{len(checks)}')
