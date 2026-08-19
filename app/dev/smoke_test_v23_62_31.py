from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(root/'main.py').read_text(encoding='utf-8')
checks=[
('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.31'),
('runtime v236231','/api/runtime-identity/v236231' in m),
('force response metadata','\"runtime_version\": \"23.62.31\"' in m),
('pazarama budget marker','V23.62.31 PAZARAMA SELECTOR-READY LATENCY BUDGET' in c),
('pazarama canonical selector','page.locator("a[href*=\'-p-\']")' in c),
('pazarama fast path marker','V23.62.31 PAZARAMA SELECTOR FAST PATH' in c),
('pazarama phase telemetry','V23.62.31 PAZARAMA SEARCH PHASE' in c),
('pazarama fast settle','pazarama_selector_fast_path_v236231' in c and '150 if selector_fast_path_v236227 else settle_timeout' in c),
('trendyol preserved','V23.62.29 TRENDYOL SELECTOR FAST PATH' in c),
('n11 recovery preserved','V23.62.30 N11 TIMEOUT SELECTOR RECOVERY' in c),
('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
('write guard preserved','DB WRITE GUARD' in (root/'BASLAT_V23_62_30.bat').read_text(encoding='utf-8')),
]
for name,ok in checks:
    if not ok: raise SystemExit('FAIL '+name)
    print('OK ',name)
