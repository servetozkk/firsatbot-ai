from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
search=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
repair=(ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
checks=[
('VERSION 23.63.27',(ROOT/'VERSION').read_text().strip()=='23.63.27'),
('VERSION.txt 23.63.27',(ROOT/'VERSION.txt').read_text().strip()=='23.63.27'),
('runtime constant','_RUNTIME_VERSION_V236323 = "23.63.27"' in main),
('runtime endpoint','/api/runtime-identity/v236327' in main),
('soak endpoint','/api/runtime-soak-stability/v236327' in main),
('Turkcell v236326 discovery preserved','V23.63.26 TURKCELL PASAJ REDMI WATCH 5 ACTIVE DIRECT DISCOVERY' in search),
('structured helper','_structured_direct_price_v236327' in retail),
('structured marker','V23.63.27 TURKCELL REDMI WATCH 5 ACTIVE STRUCTURED PRICE PROVENANCE' in retail),
('exact direct URL','xiaomi-redmi-watch-5-active-akilli-saat' in retail),
('exact identity','redmi watch 5 active' in retail and '"xiaomi" in identity_text_v236327' in retail),
('structured equals generic','abs(float(v) - generic_price) <= 0.01' in retail),
('plausible wearable price','500.0 <= generic_price <= 10000.0' in retail),
('old provenance rejection preserved','Turkcell Pasaj doğrudan satış fiyatı güvenilir provenance ile doğrulanamadı.' in retail),
('contract rejection preserved','CONTRACT_PRICE' in retail),
('installment rejection preserved','INSTALLMENT_PRICE' in retail),
('insurance rejection preserved','INSURANCE_PRICE' in retail),
('N11 v23.63.25 preserved','V23.63.25 N11 FREEBUDS SE2 WHITE VERIFIED SEARCH-CARD RECOVERY' in repair),
('HB v23.63.22 preserved','V23.63.22' in repair),
('Idefix v23.63.19 preserved','V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY' in repair),
('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for f in ['main.py','app/scrapers/retail_stores.py','app/services/cross_store_search_service.py','app/services/multi_store_offer_repair_v14_service.py','app/services/scraper_registry.py','app/scrapers/registry.py']:
    try: ast.parse((ROOT/f).read_text(encoding='utf-8')); checks.append((f'AST {f}',True))
    except Exception as e: print(e); checks.append((f'AST {f}',False))
for n,ok in checks: print(('OK  ' if ok else 'FAIL ')+n)
failed=[n for n,ok in checks if not ok]
if failed: raise SystemExit('V23.63.27 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.27 MASTER smoke OK {len(checks)}/{len(checks)}')
