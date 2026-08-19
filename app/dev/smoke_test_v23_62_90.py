from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,name):
    checks.append((bool(cond),name)); print(('OK   ' if cond else 'FAIL ')+name)
main=(ROOT/'main.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='23.62.90','VERSION 23.62.90')
ok('_RUNTIME_VERSION_V236290 = "23.62.90"' in main,'single runtime v236290')
ok('/api/runtime-identity/v236290' in main,'runtime endpoint v236290')
ok('/api/runtime-soak-stability/v236290' in main,'soak endpoint v236290')
ok('"runtime_version": _RUNTIME_VERSION_V236290' in main,'force response v236290')
ok('def _v236290_phone_title_color_signature' in repair,'Amazon title color signature')
ok('V23.62.90 AMAZON PHONE DETAIL TITLE PREFLIGHT' in repair,'color-aware title preflight telemetry')
ok('mismatch_reasons.append(f"color:' in repair,'explicit color mismatch unlocks next candidate')
ok('def _v236290_amazon_verified_phone_search_card_offer' in repair,'score280 verified card helper')
ok('if int(evidence.get("score") or 0) < 280' in repair,'score280 floor')
ok('V23.62.90 AMAZON VERIFIED PHONE SEARCH-CARD OFFER' in repair,'verified card telemetry')
ok('attached_v236290 = force_attach_candidate_offer' in repair,'price-integrity attach preserved')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
failed=[n for c,n in checks if not c]
print(f"V23.62.90 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
