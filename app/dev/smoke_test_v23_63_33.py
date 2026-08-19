from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.33',(ROOT/'VERSION').read_text().strip()=='23.63.33'),
 ('VERSION.txt 23.63.33',(ROOT/'VERSION.txt').read_text().strip()=='23.63.33'),
 ('runtime constant','_RUNTIME_VERSION_V236323 = "23.63.33"' in main),
 ('runtime endpoint','/api/runtime-identity/v236333' in main),
 ('architecture','mediamarkt-redmi-watch5-active-mat-gumus-authoritative-direct-discovery' in main),
 ('behavior policy','v23.63.32-preserved-mediamarkt-exact-wearable-discovery-only' in main),
 ('MM helper','_mediamarkt_direct_wearable_candidates_v236333' in cross),
 ('exact wearable identity','brand == "xiaomi" and family == "redmi watch 5" and variant == "active"' in cross),
 ('silver source lock','"gumus", "gümüş", "silver"' in cross),
 ('exact MediaMarkt URL','_xiaomi-redmi-watch-5-active-mat-gumus-1241001.html' in cross),
 ('MM direct evidence','v23.63.33-mediamarkt-redmi-watch5-active-mat-gumus-direct' in cross),
 ('normal MediaMarkt scraper preserved','class MediaMarktScraper' in retail),
 ('v23.63.28 price retry preserved','V23.63.28 MEDIAMARKT VERIFIED CARD PRICE DETAIL FALLBACK' in retail),
 ('FreeBuds discovery preserved','V23.63.29 TURKCELL PASAJ HUAWEI FREEBUDS SE 2 DIRECT DISCOVERY' in cross),
 ('Redmi Watch Turkcell discovery preserved','V23.63.26 TURKCELL PASAJ REDMI WATCH 5 ACTIVE DIRECT DISCOVERY' in cross),
 ('N11 preserved','V23.63.25 N11 FREEBUDS SE2 WHITE VERIFIED SEARCH-CARD RECOVERY' in repair),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py']:
 try:
  ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append((f'AST {rel}',True))
 except Exception as e: checks.append((f'AST {rel}: {e}',False))
for n,ok in checks: print(('OK  ' if ok else 'FAIL'),n)
failed=[n for n,ok in checks if not ok]
if failed: raise SystemExit('V23.63.33 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.33 MASTER smoke OK {len(checks)}/{len(checks)}')
