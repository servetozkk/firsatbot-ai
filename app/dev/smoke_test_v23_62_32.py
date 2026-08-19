from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(root/'main.py').read_text(encoding='utf-8')
checks=[
('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.32'),
('runtime v236232','/api/runtime-identity/v236232' in m),
('force response metadata','\"runtime_version\": \"23.62.32\"' in m),
('idefix strong query preserved','V23.62.24 IDEFIX STRONG-QUERY-ONLY' in c),
('idefix zero early marker','V23.62.32 IDEFIX ZERO-RESULT EARLY EXIT' in c),
('idefix zero telemetry','V23.62.32 IDEFIX SEARCH TOTAL' in c),
('idefix explicit marker policy','aradığınız kriterlere uygun ürün bulunamadı' in c and 'sonuç bulunamadı' in c),
('idefix product-anchor guard','a[href*=\'/urun/\']' in c),
('idefix bounded probe','range(8)' in c and 'page.wait_for_timeout(150)' in c),
('pazarama preserved','V23.62.31 PAZARAMA SELECTOR FAST PATH' in c),
('trendyol preserved','V23.62.29 TRENDYOL SELECTOR FAST PATH' in c),
('n11 recovery preserved','V23.62.30 N11 TIMEOUT SELECTOR RECOVERY' in c),
('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
('write guard preserved','DB WRITE GUARD' in (root/'BASLAT_V23_62_32.bat').read_text(encoding='utf-8')),
]
for name,ok in checks:
    if not ok: raise SystemExit('FAIL '+name)
    print('OK ',name)
