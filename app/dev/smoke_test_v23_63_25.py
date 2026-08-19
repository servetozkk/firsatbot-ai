from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.25',(ROOT/'VERSION').read_text().strip()=='23.63.25'),
 ('VERSION.txt 23.63.25',(ROOT/'VERSION.txt').read_text().strip()=='23.63.25'),
 ('runtime constant v236325','_RUNTIME_VERSION_V236323 = "23.63.25"' in main),
 ('runtime endpoint v236325','/api/runtime-identity/v236325' in main),
 ('soak endpoint v236325','/api/runtime-soak-stability/v236325' in main),
 ('force response exact v236325','"runtime_version": _RUNTIME_VERSION_V236323,\n            "test_only": True' in main),
 ('N11 v236325 recovery marker','V23.63.25 N11 FREEBUDS SE2 WHITE VERIFIED SEARCH-CARD RECOVERY' in repair),
 ('N11 normalization helper defined','source_corpus_v236324 = _v236283_fold(' in repair and 'recovery_url_fold_v236324 = _v236283_fold(' in repair),
 ('N11 normalized URL tokens compatible with fold','source_corpus_v236324 = _normalized_text(' not in repair and 'recovery_url_fold_v236324 = _normalized_text(' not in repair),
 ('N11 exact freebuds scope','freebuds se 2' in repair and 'is_freebuds_se2_white_source_v236324' in repair),
 ('N11 white URL lock','white_url_lock_v236324' in repair and 'ceramic white' in repair),
 ('N11 black/blue exclusion','("blue", "mavi", "black", "siyah")' in repair),
 ('N11 tight price cluster','hi_v236324 <= lo_v236324 * 1.15' in repair),
 ('N11 score 338','recovery_score_v236324 >= 338' in repair),
 ('N11 challenge bypass false','challenge_bypass=False' in repair),
 ('HB v236322 preserved','V23.63.22 HB MACBOOK NEO COMPACT CAPACITY URL LOCK' in repair),
 ('HB v236321 preserved','V23.63.21 HB VERIFIED SEARCH-CARD AUDIO-LAPTOP RECOVERY' in repair),
 ('Idefix v23.63.19 preserved','V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY' in repair),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
import ast
for rel in ['main.py','app/scrapers/hepsiburada.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py','app/services/scraper_registry.py','app/scrapers/registry.py']:
 try:
  ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append(('AST '+rel,True))
 except Exception:
  checks.append(('AST '+rel,False))
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('V23.63.25 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.25 MASTER smoke OK {len(checks)}/{len(checks)}')
