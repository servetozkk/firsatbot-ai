from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(c,m): checks.append((bool(c),m)); print(("OK   " if c else "FAIL ")+m)
main=(ROOT/"main.py").read_text(encoding="utf-8")
repair=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
ok((ROOT/"VERSION").read_text(encoding="utf-8").strip()=="23.62.89","VERSION 23.62.89")
ok('_RUNTIME_VERSION_V236289 = "23.62.89"' in main,"single runtime v236289")
ok('/api/runtime-identity/v236289' in main,"runtime endpoint v236289")
ok('/api/runtime-soak-stability/v236289' in main,"soak endpoint v236289")
ok('"runtime_version": _RUNTIME_VERSION_V236289' in main,"force response v236289")
ok('def _v236289_amazon_verified_phone_search_card_offer' in repair,"Amazon verified phone card helper")
ok('V23.62.89 AMAZON VERIFIED PHONE SEARCH-CARD OFFER' in repair,"Amazon phone card telemetry")
ok('int(evidence.get("score") or 0) < 316' in repair,"score316 floor")
ok('source_price * 0.45 <= prices[0] <= source_price * 1.75' in repair,"plausible price band")
ok('_v236287_phone_family_signature(title)' in repair,"detail family verification")
ok('_v236283_phone_variant_signature(title)' in repair,"detail variant verification")
ok('_v236287_phone_storage_signature(title)' in repair,"detail storage verification")
ok('attached_v236289 = force_attach_candidate_offer' in repair,"price-integrity attach preserved")
ok('security_challenge_bypass": "disabled"' in main,"security bypass disabled")
failed=[m for c,m in checks if not c]
print(f"V23.62.89 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
