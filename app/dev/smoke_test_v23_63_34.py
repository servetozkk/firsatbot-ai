from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.34',(ROOT/'VERSION').read_text().strip()=='23.63.34'),
 ('VERSION.txt 23.63.34',(ROOT/'VERSION.txt').read_text().strip()=='23.63.34'),
 ('runtime constant','_RUNTIME_VERSION_V236323 = "23.63.34"' in main),
 ('runtime endpoint','/api/runtime-identity/v236334' in main),
 ('architecture','turkcell-macbook-neo-8gb-256gb-authoritative-direct-discovery' in main),
 ('behavior policy','v23.63.33-preserved-turkcell-exact-macbook-neo-discovery-only' in main),
 ('MacBook helper','_turkcell_pasaj_direct_macbook_neo_candidates_v236334' in cross),
 ('exact family','brand == "apple" and family == "macbook neo"' in cross),
 ('RAM lock','ram_gb == 8' in cross),
 ('storage lock','storage_gb == 256' in cross),
 ('exact URL','apple-macbook-neo-a18-pro-cip-13-inc-6-cekirdekli-cpu-5-cekirdekli-gpu-8gb-256' in cross),
 ('direct evidence','v23.63.34-turkcell-macbook-neo-8gb-256gb-direct' in cross),
 ('MM 6333 preserved','v23.63.33-mediamarkt-redmi-watch5-active-mat-gumus-direct' in cross),
 ('FreeBuds preserved','v23.63.29-turkcell-huawei-freebuds-se2-direct' in cross),
 ('Redmi Watch Turkcell preserved','v23.63.26-turkcell-redmi-watch5-active-direct' in cross),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py']:
 ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append(('AST '+rel,True))
failed=[name for name,ok in checks if not ok]
for name,ok in checks: print(('OK   ' if ok else 'FAIL ')+name)
if failed: raise SystemExit('V23.63.34 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.34 MASTER smoke OK {len(checks)}/{len(checks)}')
