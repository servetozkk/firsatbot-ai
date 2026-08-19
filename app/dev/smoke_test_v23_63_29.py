from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
checks=[]
def ok(cond,name):
    checks.append((name,bool(cond)))
    print(('OK  ' if cond else 'FAIL ')+name)
ok((ROOT/'VERSION').read_text().strip()=='23.63.29','VERSION 23.63.29')
ok((ROOT/'VERSION.txt').read_text().strip()=='23.63.29','VERSION.txt 23.63.29')
ok('_RUNTIME_VERSION_V236323 = "23.63.29"' in main,'runtime constant')
ok('/api/runtime-identity/v236329' in main,'runtime endpoint')
ok('turkcell-huawei-freebuds-se2-authoritative-direct-discovery' in main,'architecture')
ok('V23.63.29 TURKCELL PASAJ HUAWEI FREEBUDS SE 2 DIRECT DISCOVERY' in search,'FreeBuds direct discovery marker')
ok('generic_model_family' in search and 'freebuds se 2' in search,'strong generic family scope')
ok('brand == "huawei"' in search,'Huawei exact brand lock')
ok('huawei-freebuds-se-2-bluetooth-kulaklik' in search,'exact Pasaj URL lock')
ok('v23.63.29-turkcell-huawei-freebuds-se2-direct' in search,'candidate provenance marker')
ok('direct_wearable_v236326' in search,'Turkcell wearable v23.63.26 preserved')
ok('V23.63.27 TURKCELL REDMI WATCH 5 ACTIVE STRUCTURED PRICE PROVENANCE' in retail,'Turkcell price provenance v23.63.27 preserved')
ok('mediamarkt_redmi_note15pro_price_retry' in main,'MediaMarkt v23.63.28 preserved')
ok('n11_freebuds_se2_white_search_card_recovery' in main,'N11 v23.63.25 preserved')
ok('hepsiburada_verified_search_card_recovery' in main,'HB v23.63.21 preserved')
ok('idefix_curated_canonical_evidence' in main,'Idefix v23.63.19 preserved')
ok('"security_challenge_bypass": "disabled"' in main,'no challenge bypass')
ok('"price_integrity_quarantine": "preserved"' in main,'price integrity preserved')
for rel in ['main.py','app/services/cross_store_search_service.py','app/scrapers/retail_stores.py','app/services/multi_store_offer_repair_v14_service.py']:
    try:
        ast.parse((ROOT/rel).read_text(encoding='utf-8'))
        ok(True,'AST '+rel)
    except Exception:
        ok(False,'AST '+rel)
failed=[n for n,v in checks if not v]
if failed: raise SystemExit('V23.63.29 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.29 MASTER smoke OK {len(checks)}/{len(checks)}')
