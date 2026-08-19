from pathlib import Path
root=Path(__file__).resolve().parents[2]
main=(root/"main.py").read_text(encoding="utf-8")
smart=(root/"app/services/smart_catalog_refresh_v218_service.py").read_text(encoding="utf-8")
multi=(root/"app/services/multi_store_service.py").read_text(encoding="utf-8")
cross=(root/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
repair=(root/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
checks=[
 ("VERSION",(root/"VERSION").read_text().strip()=="23.62.66"),
 ("runtime v236266",'/api/runtime-identity/v236266' in main),
 ("soak v236266",'/api/runtime-soak-stability/v236266' in main),
 ("single source v236266",'_RUNTIME_VERSION_V236266 = "23.62.66"' in main),
 ("force uses v236266",'"runtime_version": _RUNTIME_VERSION_V236266' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):]),
 ("force due inclusion preserved",'V23.62.65 N11 FORCE DUE-SET INCLUSION' in smart),
 ("post cap invariant preserved",'V23.62.64 N11 POST-CAP FORCE INCLUSION' in cross),
 ("store sku convergence preserved",'V23.62.65 OFFER UNIQUE-KEY CONVERGENCE' in multi),
 ("url convergence marker",'V23.62.66 OFFER URL UNIQUE-KEY CONVERGENCE' in multi),
 ("url owner checked",'ProductOffer.url == url' in multi),
 ("conflicting url not assigned",'action=preserve-existing-target-url' in multi),
 ("url helper used primary",'_v236266_assign_offer_url_conflict_safe(db, offer, product.url)' in multi),
 ("url helper used exact",'_v236266_assign_offer_url_conflict_safe(db, exact_store_offer, product.url)' in multi),
 ("persisted trust marker",'V23.62.66 N11 PERSISTED EXACT-URL TRUST BOOTSTRAP' in repair),
 ("persisted trust same global",'GlobalOffer.global_product_id == int(target_global_product_id)' in repair),
 ("persisted trust n11",'GlobalOffer.store_code == "n11"' in repair),
 ("persisted trust exact url",'GlobalOffer.url == url' in repair),
 ("persisted trust active",'GlobalOffer.is_active.is_(True)' in repair and 'GlobalOffer.is_hidden.is_(False)' in repair),
 ("persisted trust recent",'timedelta(hours=24)' in repair),
 ("recent bridge preserved",'V23.62.62 N11 RECENT DETAIL TRUST BRIDGE' in repair),
 ("verified recovery preserved",'V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
 ("shared session preserved",'V23.62.60 N11 DETAIL HTTP CONNECTION' in (root/'app/scrapers/generic_store.py').read_text(encoding='utf-8')),
 ("security bypass disabled",'"security_challenge_bypass": "disabled"' in main),
 ("price integrity preserved",'"price_integrity_quarantine": "preserved"' in main),
]
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
print(f"V23.62.66 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed: raise SystemExit(1)
