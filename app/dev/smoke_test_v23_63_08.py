from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/'main.py').read_text(encoding='utf-8')
cross=(ROOT/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
retail=(ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
svc=(ROOT/'app/services/scraper_registry.py').read_text(encoding='utf-8')
reg=(ROOT/'app/scrapers/registry.py').read_text(encoding='utf-8')
adreg=(ROOT/'app/stores/adapters/registry.py').read_text(encoding='utf-8')
ad=(ROOT/'app/stores/adapters/pttavm.py').read_text(encoding='utf-8')
eco=(ROOT/'app/services/store_ecosystem_v13_8_0.py').read_text(encoding='utf-8')
scan=(ROOT/'app/services/scan_service.py').read_text(encoding='utf-8')
admin=(ROOT/'app/web/admin_scraper_routes.py').read_text(encoding='utf-8')
checks=[
 ('VERSION 23.63.08',(ROOT/'VERSION').read_text().strip()=='23.63.08'),
 ('VERSION.txt 23.63.08',(ROOT/'VERSION.txt').read_text().strip()=='23.63.08'),
 ('runtime endpoint v236308','/api/runtime-identity/v236308' in main),
 ('soak endpoint v236308','/api/runtime-soak-stability/v236308' in main),
 ('force response v236308','"runtime_version": _RUNTIME_VERSION_V236308' in main),
 ('PttAVM search definition','code="pttavm"' in cross and 'https://www.pttavm.com/arama?q={query}' in cross),
 ('PttAVM priority','"pttavm": 86' in cross),
 ('PttAVM adapter','PTTAVM_ADAPTER' in ad and '-p-' in ad),
 ('PttAVM adapter registry','PTTAVM_ADAPTER.code' in adreg),
 ('PttAVM retail config','"pttavm": GenericStoreConfig' in retail),
 ('PttAVM scraper class','class PttAVMScraper' in retail),
 ('PttAVM service registry','code="pttavm"' in svc and 'PttAVMScraper' in svc),
 ('PttAVM duplicate registry','code="pttavm"' in reg and 'PttAVMScraper' in reg),
 ('PttAVM ecosystem active','StoreCapability("pttavm", "PttAVM", ("pttavm.com",), True' in eco),
 ('PttAVM scan URL contract','if "pttavm.com" in host:' in scan and '-p-' in scan),
 ('PttAVM admin host mapping','if "pttavm" in host:' in admin),
 ('Teknosa preserved','code="teknosa"' in cross and 'TeknosaScraper' in svc),
 ('force budget 13','"force_store_budget": 13' in main),
 ('security bypass disabled','"security_challenge_bypass": "disabled"' in main),
 ('price integrity preserved','"price_integrity_quarantine": "preserved"' in main),
]
for rel in ['main.py','app/services/cross_store_search_service.py','app/scrapers/retail_stores.py','app/services/scraper_registry.py','app/scrapers/registry.py','app/stores/adapters/pttavm.py','app/stores/adapters/registry.py','app/services/scan_service.py','app/web/admin_scraper_routes.py']:
    try:
        ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks.append((f'AST {rel}',True))
    except Exception:
        checks.append((f'AST {rel}',False))
failed=[]
for name,ok in checks:
    print(('OK  ' if ok else 'FAIL'),name)
    if not ok: failed.append(name)
if failed: raise SystemExit('V23.63.08 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.08 MASTER smoke OK {len(checks)}/{len(checks)}')
