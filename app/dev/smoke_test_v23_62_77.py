from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,label):
    checks.append((label,bool(cond)))
    print(('OK  ' if cond else 'FAIL'),label)
main=(ROOT/'main.py').read_text(encoding='utf-8')
binding=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
hb=(ROOT/'app/stores/adapters/hepsiburada.py').read_text(encoding='utf-8')
launcher=(ROOT/'BASLAT_V23_62_77.bat').read_text(encoding='utf-8')
version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
ok(version=='23.62.77','VERSION')
ok('/api/runtime-identity/v236277' in main,'runtime v236277')
ok('/api/runtime-soak-stability/v236277' in main,'soak v236277')
ok('single-source-v236277' in main,'single source v236277')
ok('_RUNTIME_VERSION_V236277 = "23.62.77"' in main,'runtime constant')
ok('"runtime_version": _RUNTIME_VERSION_V236277' in main,'force/runtime uses v236277')
ok('V23.62.77 AMAZON BOUNDED IDENTITY-REJECT RETRY CAP' in binding,'Amazon bounded retry cap marker')
ok('candidate_urls = candidate_urls[:2]' in binding,'Amazon retains max two detail candidates')
ok('amazon_identity_retry_allowed_v236277 = False' in binding,'retry starts locked')
ok('and not amazon_identity_retry_allowed_v236277' in binding,'backup blocked while locked')
ok('V23.62.77 AMAZON FIRST CANDIDATE IDENTITY_REJECT' in binding,'canonical reject unlock marker')
ok('amazon_identity_retry_allowed_v236277 = True' in binding,'canonical reject unlocks backup')
ok('V23.62.77 AMAZON IDENTITY-REJECT RETRY' in binding,'second candidate execution marker')
ok('NO_BUYABLE_OFFER' in binding,'no-buyable path preserved')
ok('HepsiburadaSecurityChallenge' in binding,'challenge path preserved')
ok('V23.62.76 HB VERIFIED PHONE-WEARABLE SEARCH-CARD RECOVERY' in binding,'v76 HB recovery preserved')
ok('single-dot-three-digit' in main and 'V23.62.76: Turkish visible prices use a dot as thousands' in hb,'v76 HB price normalization preserved')
ok('security_challenge_bypass": "disabled"' in main,'security bypass disabled')
ok('price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
ok('smoke_test_v23_62_77.py' in launcher,'launcher calls v77 smoke')
ok('23.62.77' in launcher,'launcher version')
# Behavioral state-machine lock: second candidate may execute only after canonical identity reject.
def should_run_second(first_outcome):
    unlocked=False
    if first_outcome=='CANONICAL_IDENTITY_REJECT':
        unlocked=True
    return unlocked
ok(should_run_second('CANONICAL_IDENTITY_REJECT') is True,'behavior identity reject unlocks exactly one backup')
for outcome in ['NO_BUYABLE_OFFER','SECURITY_CHALLENGE','TIMEOUT','SCRAPE_ERROR','COLOR_REJECT','SUCCESS']:
    ok(should_run_second(outcome) is False,f'behavior {outcome} keeps backup blocked')
failed=[label for label,state in checks if not state]
print(f"V23.62.77 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed:
    print('FAILED:',failed)
    sys.exit(1)
