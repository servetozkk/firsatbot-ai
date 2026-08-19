from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
hb=(ROOT/'app/scrapers/hepsiburada.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.22',(ROOT/'VERSION').read_text().strip()=='23.63.22'),
 ('VERSION.txt 23.63.22',(ROOT/'VERSION.txt').read_text().strip()=='23.63.22'),
 ('runtime constant v236322','_RUNTIME_VERSION_V236322 = "23.63.22"' in main),
 ('runtime endpoint v236322','/api/runtime-identity/v236322' in main),
 ('soak endpoint v236322','/api/runtime-soak-stability/v236322' in main),
 ('force response exact v236322','"runtime_version": _RUNTIME_VERSION_V236322,\n            "test_only": True' in main),
 ('HB v236321 recovery preserved','V23.63.21 HB VERIFIED SEARCH-CARD AUDIO-LAPTOP RECOVERY' in repair),
 ('HB MacBook compact storage token','f"{storage_v236321.group(1)}gb" in urlf' in repair),
 ('HB MacBook compact ram token','f"{ram_v236321.group(1)}gb" in urlf' in repair),
 ('HB v236322 diagnostic','V23.63.22 HB MACBOOK NEO COMPACT CAPACITY URL LOCK' in repair),
 ('HB trusted final required','dom-hepsiburada-final-price' in repair and 'trusted_hb_final' in repair),
 ('HB challenge bypass false','challenge_bypass=False' in repair),
 ('HB bounded recheck preserved','enumerate((1_000, 2_000), start=1)' in hb and 'fail_closed=True' in hb),
 ('HB HTTP2 retry preserved','V23.63.16 HEPSIBURADA TRANSIENT HTTP2 NAVIGATION RETRY' in cross),
 ('Idefix v23.63.19 preserved','V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY' in repair),
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
if failed: raise SystemExit('V23.63.22 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.22 MASTER smoke OK {len(checks)}/{len(checks)}')
