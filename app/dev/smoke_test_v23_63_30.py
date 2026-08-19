from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
('VERSION 23.63.30',(ROOT/'VERSION').read_text().strip()=='23.63.30'),
('VERSION.txt 23.63.30',(ROOT/'VERSION.txt').read_text().strip()=='23.63.30'),
('runtime constant','_RUNTIME_VERSION_V236323 = "23.63.30"' in main),
('runtime endpoint','/api/runtime-identity/v236330' in main),
('architecture','turkcell-huawei-freebuds-se2-structured-price-provenance' in main),
('FreeBuds discovery v23.63.29 preserved','V23.63.29 TURKCELL PASAJ HUAWEI FREEBUDS SE 2 DIRECT DISCOVERY' in search),
('structured helper reused','_structured_direct_price_v236327' in retail),
('FreeBuds structured marker','V23.63.30 TURKCELL HUAWEI FREEBUDS SE 2 STRUCTURED PRICE PROVENANCE' in retail),
('exact FreeBuds URL','huawei-freebuds-se-2-bluetooth-kulaklik' in retail),
('exact Huawei identity','"huawei" in identity_text_v236330' in retail),
('exact FreeBuds identity','"freebuds se 2" in identity_text_v236330' in retail),
('structured equals generic','abs(float(v) - generic_price) <= 0.01' in retail),
('plausible audio bound','300.0 <= generic_price <= 10000.0' in retail),
('old provenance rejection preserved','Turkcell Pasaj doğrudan satış fiyatı güvenilir provenance ile doğrulanamadı.' in retail),
('Redmi Watch provenance preserved','V23.63.27 TURKCELL REDMI WATCH 5 ACTIVE STRUCTURED PRICE PROVENANCE' in retail),
('MediaMarkt v23.63.28 preserved','V23.63.28 MEDIAMARKT' in repair or 'V23.63.28 MEDIAMARKT' in retail),
('N11 v23.63.25 preserved','V23.63.25 N11 FREEBUDS SE2 WHITE VERIFIED SEARCH-CARD RECOVERY' in repair),
('HB v23.63.21 preserved','V23.63.21' in repair),
('Idefix v23.63.19 preserved','V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY' in repair),
('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for f in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py']:
    try: ast.parse((ROOT/f).read_text(encoding='utf-8')); checks.append((f'AST {f}',True))
    except Exception as e: print(e); checks.append((f'AST {f}',False))
for n,ok in checks: print(('OK  ' if ok else 'FAIL ')+n)
failed=[n for n,ok in checks if not ok]
if failed: raise SystemExit('V23.63.30 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.30 MASTER smoke OK {len(checks)}/{len(checks)}')
