from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
svc=(ROOT/'app/services/scraper_registry.py').read_text(encoding='utf-8')
reg=(ROOT/'app/scrapers/registry.py').read_text(encoding='utf-8')
ad=(ROOT/'app/stores/adapters/beymen.py').read_text(encoding='utf-8')
adreg=(ROOT/'app/stores/adapters/registry.py').read_text(encoding='utf-8')
eco=(ROOT/'app/services/store_ecosystem_v13_8_0.py').read_text(encoding='utf-8')
scan=(ROOT/'app/services/scan_service.py').read_text(encoding='utf-8')
admin=(ROOT/'app/web/admin_scraper_routes.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.10',(ROOT/'VERSION').read_text().strip()=='23.63.10'),
 ('runtime endpoint v236310','/api/runtime-identity/v236310' in main),
 ('soak endpoint v236310','/api/runtime-soak-stability/v236310' in main),
 ('force response v236310','"runtime_version": _RUNTIME_VERSION_V236310' in main),
 ('Beymen search definition','code="beymen"' in cross and 'https://www.beymen.com/tr/cep-telefonu-95941' in cross),
 ('Beymen priority','"beymen": 85' in cross),
 ('Beymen adapter','BEYMEN_ADAPTER' in ad and '/tr/p_' in ad),
 ('Beymen adapter registry','BEYMEN_ADAPTER.code' in adreg),
 ('Beymen retail config','"beymen": GenericStoreConfig' in retail),
 ('Beymen scraper class','class BeymenScraper' in retail),
 ('Beymen service registry','code="beymen"' in svc and 'BeymenScraper' in svc),
 ('Beymen duplicate registry','code="beymen"' in reg and 'BeymenScraper' in reg),
 ('Beymen ecosystem active','StoreCapability("beymen", "Beymen", ("beymen.com",), True' in eco),
 ('Beymen URL contract','if "beymen.com" in host:' in scan and '/tr/p_' in scan),
 ('Beymen admin host mapping','if "beymen" in host:' in admin),
 ('PttAVM preserved','code="pttavm"' in cross and 'PttAVMScraper' in svc),
 ('Teknosa preserved','code="teknosa"' in cross),
 ('force budget 14','"force_store_budget": 14' in main),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/services/cross_store_search_service.py','app/scrapers/retail_stores.py','app/services/scraper_registry.py','app/scrapers/registry.py','app/stores/adapters/beymen.py','app/stores/adapters/registry.py','app/services/scan_service.py','app/web/admin_scraper_routes.py']:
    try: ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append(('AST '+rel,True))
    except Exception: checks.append(('AST '+rel,False))
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL'),name)
 if not ok: failed.append(name)
if failed: raise SystemExit('V23.63.10 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.10 MASTER smoke OK {len(checks)}/{len(checks)}')
