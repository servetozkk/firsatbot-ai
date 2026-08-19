from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
hb=(ROOT/'app/scrapers/hepsiburada.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.20',(ROOT/'VERSION').read_text().strip()=='23.63.20'),
 ('VERSION.txt 23.63.20',(ROOT/'VERSION.txt').read_text().strip()=='23.63.20'),
 ('runtime constant v236320','_RUNTIME_VERSION_V236320 = "23.63.20"' in main),
 ('runtime endpoint v236320','/api/runtime-identity/v236320' in main),
 ('soak endpoint v236320','/api/runtime-soak-stability/v236320' in main),
 ('force response exact v236320','"runtime_version": _RUNTIME_VERSION_V236320,\n            "test_only": True' in main),
 ('HB exactly two bounded waits','enumerate((1_000, 2_000), start=1)' in hb),
 ('HB challenge progress /2','challenge kontrolü {attempt}/2' in hb),
 ('HB v236320 telemetry','V23.63.20 HB BOUNDED CHALLENGE RECHECK:' in hb),
 ('HB exhausted fail closed','V23.63.20 HB BOUNDED CHALLENGE RECHECK EXHAUSTED' in hb and 'fail_closed=True' in hb),
 ('HB bypass false telemetry','bypass=False' in hb),
 ('HB HTTP2 retry preserved','V23.63.16 HEPSIBURADA TRANSIENT HTTP2 NAVIGATION RETRY' in cross),
 ('Idefix v23.63.19 preserved','canonical_evidence_label_v236319' in cross and 'V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY' in repair),
 ('PttAVM v23.63.15 preserved','V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY' in cross),
 ('Turkcell v23.63.14 preserved','V23.63.14 TURKCELL IOS CANONICAL CANDIDATE IDENTITY OVERRIDE' in repair),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for p in [ROOT/'main.py',ROOT/'app/scrapers/hepsiburada.py',ROOT/'app/services/cross_store_search_service.py',ROOT/'app/services/multi_store_offer_repair_v14_service.py',ROOT/'app/services/scraper_registry.py',ROOT/'app/scrapers/registry.py']:
    try: ast.parse(p.read_text(encoding='utf-8')); checks.append((f'AST {p.relative_to(ROOT)}',True))
    except Exception: checks.append((f'AST {p.relative_to(ROOT)}',False))
for name,ok in checks: print(('OK  ' if ok else 'FAIL ')+name)
failed=[name for name,ok in checks if not ok]
if failed: raise SystemExit('V23.63.20 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.20 MASTER smoke OK {len(checks)}/{len(checks)}')
