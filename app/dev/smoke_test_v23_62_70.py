from pathlib import Path
root=Path(__file__).resolve().parents[2]
main=(root/'main.py').read_text(encoding='utf-8')
search=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
amazon=(root/'app/scrapers/amazon.py').read_text(encoding='utf-8')
smart=(root/'app/services/smart_catalog_refresh_v218_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(root/'VERSION').read_text().strip()=='23.62.70'),
 ('runtime v236270','/api/runtime-identity/v236270' in main),
 ('soak v236270','/api/runtime-soak-stability/v236270' in main),
 ('single source v236270','_RUNTIME_VERSION_V236270 = "23.62.70"' in main),
 ('force uses v236270','"runtime_version": _RUNTIME_VERSION_V236270' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):]),
 ('v69 phone accessory preserved','"nano cam"' in search and '"seramik film"' in search and '"jelatin"' in search),
 ('amazon nav 15s preserved','navigation_timeout_ms=15_000' in amazon),
 ('amazon exact search first','definition.code == "amazon"' in search and 'search_query,\n                generic_exact_v23620' in search),
 ('amazon no-buyable circuit break','V23.62.70 AMAZON NO-BUYABLE CIRCUIT BREAK' in search),
 ('amazon no-buyable break','if definition.code == "amazon":' in search and 'break\n                    continue' in search),
 ('store budget v68 preserved','V23.62.68 FORCE STORE-BUDGET CONTRACT' in smart),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
 ('launcher exists',(root/'BASLAT_V23_62_70.bat').exists()),
 ('launcher calls v70 smoke','smoke_test_v23_62_70.py' in (root/'BASLAT_V23_62_70.bat').read_text(encoding='utf-8')),
]
failed=[name for name,ok in checks if not ok]
for name,ok in checks: print(('OK  ' if ok else 'FAIL'),name)
print(f"V23.62.70 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed: raise SystemExit(1)
