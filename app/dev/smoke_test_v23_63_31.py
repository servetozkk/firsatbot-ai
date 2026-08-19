from pathlib import Path
import ast, re
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
('VERSION 23.63.31',(ROOT/'VERSION').read_text().strip()=='23.63.31'),
('VERSION.txt 23.63.31',(ROOT/'VERSION.txt').read_text().strip()=='23.63.31'),
('runtime constant','_RUNTIME_VERSION_V236323 = "23.63.31"' in main),
('runtime endpoint','/api/runtime-identity/v236331' in main),
('architecture','turkcell-freebuds-se2-authoritative-labeled-white-color' in main),
('discovery preserved','V23.63.29 TURKCELL PASAJ HUAWEI FREEBUDS SE 2 DIRECT DISCOVERY' in search),
('price provenance preserved','V23.63.30 TURKCELL HUAWEI FREEBUDS SE 2 STRUCTURED PRICE PROVENANCE' in retail),
('labeled color marker','V23.63.31 TURKCELL FREEBUDS SE2 AUTHORITATIVE LABELED COLOR' in retail),
('override marker','V23.63.31 TURKCELL FREEBUDS SE2 AUTHORITATIVE COLOR OVERRIDE' in retail),
('exact url lock','huawei-freebuds-se-2-bluetooth-kulaklik' in retail),
('two label threshold','len(set(white_labels_v236331)) >= 2' in retail),
('conflict fail closed','and not conflicting_labels_v236331' in retail),
('original color label','(?:orjinal|orijinal)' in retail),
('main color label','ana\\s+renk' in retail or 'ana\s+renk' in retail),
('normal matcher preserved','V23.32 audio kesin red: renk farklı' in (ROOT/'app/services/category_aware_matcher_v221.py').read_text(encoding='utf-8')),
('N11 preserved','V23.63.25 N11 FREEBUDS SE2 WHITE VERIFIED SEARCH-CARD RECOVERY' in repair),
('HB preserved','V23.63.21' in repair),
('Idefix preserved','V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY' in repair),
('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for f in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py']:
    try: ast.parse((ROOT/f).read_text(encoding='utf-8')); checks.append((f'AST {f}',True))
    except Exception as e: print(e); checks.append((f'AST {f}',False))
for n,ok in checks: print(('OK  ' if ok else 'FAIL ')+n)
failed=[n for n,ok in checks if not ok]
if failed: raise SystemExit('V23.63.31 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.31 MASTER smoke OK {len(checks)}/{len(checks)}')
