from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
('VERSION 23.63.26',(ROOT/'VERSION').read_text().strip()=='23.63.26'),
('VERSION.txt 23.63.26',(ROOT/'VERSION.txt').read_text().strip()=='23.63.26'),
('runtime constant','_RUNTIME_VERSION_V236323 = "23.63.26"' in main),
('runtime endpoint','/api/runtime-identity/v236326' in main),
('soak endpoint','/api/runtime-soak-stability/v236326' in main),
('Turkcell wearable helper','_turkcell_pasaj_direct_wearable_candidates_v236326' in search),
('Turkcell marker','V23.63.26 TURKCELL PASAJ REDMI WATCH 5 ACTIVE DIRECT DISCOVERY' in search),
('exact family lock','family == "redmi watch 5"' in search),
('exact active lock','variant == "active"' in search),
('exact xiaomi lock','brand == "xiaomi"' in search),
('direct URL','xiaomi-redmi-watch-5-active-akilli-saat' in search),
('normal detail path preserved','return direct_wearable_v236326[: self.candidate_limit]' in search),
('N11 v23.63.25 preserved','V23.63.25 N11 FREEBUDS SE2 WHITE VERIFIED SEARCH-CARD RECOVERY' in (ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')),
('HB v23.63.22 preserved','V23.63.22' in (ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')),
('Idefix v23.63.19 preserved','V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY' in repair),
('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for p in ['main.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py','app/services/scraper_registry.py','app/scrapers/registry.py']:
    try: ast.parse((ROOT/p).read_text(encoding='utf-8')); checks.append((f'AST {p}',True))
    except Exception: checks.append((f'AST {p}',False))
for n,ok in checks: print(('OK  ' if ok else 'FAIL ')+n)
failed=[n for n,ok in checks if not ok]
if failed: raise SystemExit('V23.63.26 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.26 MASTER smoke OK {len(checks)}/{len(checks)}')
