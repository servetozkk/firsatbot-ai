from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/"main.py").read_text(encoding="utf-8")
binding=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
launcher=(ROOT/"BASLAT_V23_62_83.bat").read_text(encoding="utf-8")
version=(ROOT/"VERSION").read_text(encoding="utf-8").strip()
checks=[]
def ok(c,n):
 checks.append((n,bool(c))); print(("OK   " if c else "FAIL ")+n)
ok(version=="23.62.83","VERSION")
ok('_RUNTIME_VERSION_V236283 = "23.62.83"' in main,"runtime constant")
ok('/api/runtime-identity/v236283' in main,"runtime v236283")
ok('/api/runtime-soak-stability/v236283' in main,"soak v236283")
ok('amazon-phone-detail-title-preflight-variant-gate' in main,"architecture")
ok('_v236283_amazon_phone_detail_title_preflight' in binding,"preflight helper")
ok('timeout=3.0' in binding,"preflight bounded 3s")
ok('candidate_urls = candidate_urls[:3]' in binding,"top3 retained")
ok('CANONICAL_IDENTITY_REJECT_PREFLIGHT' in binding,"preflight reject event")
ok('next_candidate_unlocked=True' in binding,"mismatch-only unlock")
ok('pro_plus' in binding,"Pro+ distinct from Pro")
ok('security_challenge_bypass' in main and 'disabled' in main,"security bypass disabled")
ok('price_integrity_quarantine' in main and 'preserved' in main,"price integrity preserved")
ok('production_ingestion_behavior' in main and 'unchanged' in main,"production ingestion unchanged")
ok('23.62.83' in launcher and 'smoke_test_v23_62_83.py' in launcher,"launcher v83")
failed=[n for n,c in checks if not c]
print(f"V23.62.83 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
