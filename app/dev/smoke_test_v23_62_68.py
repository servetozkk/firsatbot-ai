from pathlib import Path
import hashlib, json
root=Path(__file__).resolve().parents[2]
main=(root/"main.py").read_text(encoding="utf-8")
smart=(root/"app/services/smart_catalog_refresh_v218_service.py").read_text(encoding="utf-8")
manifest=json.loads((root/"V23_62_68_BASELINE_FINGERPRINTS.json").read_text(encoding="utf-8"))
checks=[
 ("VERSION",(root/"VERSION").read_text().strip()=="23.62.68"),
 ("runtime v236268",'/api/runtime-identity/v236268' in main),
 ("soak v236268",'/api/runtime-soak-stability/v236268' in main),
 ("single source v236268",'_RUNTIME_VERSION_V236268 = "23.62.68"' in main),
 ("force uses v236268",'"runtime_version": _RUNTIME_VERSION_V236268' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]),
 ("budget marker",'V23.62.68 FORCE STORE-BUDGET CONTRACT' in smart),
 ("budget captured before n11 append",smart.find('force_store_budget_v236268 = len(searchable_codes)') < smart.find('searchable_codes.append("n11")')),
 ("budget trim after allow filter",smart.find('V23.62.68 FORCE STORE-BUDGET CONTRACT') > smart.find('if allowed_store_codes is not None:')),
 ("n11 preserved",'and "n11" in searchable_codes' in smart),
 ("minimum offer floor",'minimum_offer_count' in main and ' < _SOAK_V236248_EXPECTED_OFFERS' in main),
 ("minimum success floor",'minimum_store_success_count' in main and ' < _SOAK_V236248_EXPECTED_SUCCESS_STORES' in main),
 ("extra valid allowed",'minimum-floor-extra-valid-offers-allowed' in main),
 ("n11 success contract",'"n11_expected_status": "SUCCESS"' in main),
 ("security bypass disabled",'"security_challenge_bypass": "disabled"' in main),
 ("price integrity preserved",'"price_integrity_quarantine": "preserved"' in main),
 ("launcher exists",(root/"BASLAT_V23_62_68.bat").exists()),
 ("launcher calls v68 smoke",'smoke_test_v23_62_68.py' in (root/"BASLAT_V23_62_68.bat").read_text(encoding="utf-8")),
]
for rel,expected in manifest["files"].items():
 actual=hashlib.sha256((root/rel).read_bytes()).hexdigest()
 checks.append((f"fingerprint {rel}",actual==expected))
failed=[]
for name,ok in checks:
 print(("OK  " if ok else "FAIL ")+name)
 if not ok: failed.append(name)
print(f"V23.62.68 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed: raise SystemExit(1)
