from pathlib import Path
import hashlib, json
root=Path(__file__).resolve().parents[2]
main=(root/"main.py").read_text(encoding="utf-8")
manifest=json.loads((root/"V23_62_67_BASELINE_FINGERPRINTS.json").read_text(encoding="utf-8"))
checks=[
 ("VERSION",(root/"VERSION").read_text().strip()=="23.62.67"),
 ("runtime v236267",'/api/runtime-identity/v236267' in main),
 ("soak v236267",'/api/runtime-soak-stability/v236267' in main),
 ("single source v236267",'_RUNTIME_VERSION_V236267 = "23.62.67"' in main),
 ("force uses v236267",'"runtime_version": _RUNTIME_VERSION_V236267' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]),
 ("baseline architecture",'"architecture": "production-stability-baseline-lock"' in main),
 ("baseline source",'"baseline_source": "v23.62.66-15-of-15-soak-pass"' in main),
 ("baseline runs 15",'"baseline_observed_run_count": 15' in main),
 ("baseline violations 0",'"baseline_contract_violation_run_count": 0' in main),
 ("baseline offers 6",'"baseline_offer_count": 6' in main),
 ("baseline store success 6",'"baseline_store_success_count": 6' in main),
 ("baseline n11 15",'"baseline_n11_observations": 15' in main and '"baseline_n11_success_count": 15' in main),
 ("baseline n11 100",'"baseline_n11_success_rate_percent": 100.0' in main),
 ("scraping frozen",'"scraping_behavior": "v23.62.66-frozen"' in main),
 ("expected offer contract",'"expected_offer_count": 6' in main),
 ("expected success contract",'"expected_store_success_count": 6' in main),
 ("n11 success contract",'"n11_expected_status": "SUCCESS"' in main),
 ("security bypass disabled",'"security_challenge_bypass": "disabled"' in main),
 ("price integrity preserved",'"price_integrity_quarantine": "preserved"' in main),
 ("launcher exists",(root/"BASLAT_V23_62_67.bat").exists()),
 ("launcher calls v67 smoke",'smoke_test_v23_62_67.py' in (root/"BASLAT_V23_62_67.bat").read_text(encoding="utf-8")),
]
for rel,expected in manifest["files"].items():
    actual=hashlib.sha256((root/rel).read_bytes()).hexdigest()
    checks.append((f"fingerprint {rel}",actual==expected))
failed=[]
for name,ok in checks:
 print(("OK  " if ok else "FAIL ")+name)
 if not ok: failed.append(name)
print(f"V23.62.67 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed: raise SystemExit(1)
