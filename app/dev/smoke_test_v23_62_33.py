from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(root/'main.py').read_text(encoding='utf-8')
checks=[
('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.33'),
('runtime v236233','/api/runtime-identity/v236233' in m),
('force response metadata','\"runtime_version\": \"23.62.33\"' in m),
('n11 v236233 marker','V23.62.33 N11 QUERY ORDER' in c),
('strong brand model condition','len(generic_model_only_v23620.split()) >= 2' in c),
('brand model first branch','if n11_strong_brand_model_v236233' in c and 'generic_exact_v23620,\n                    generic_model_only_v23620' in c),
('weak model first preserved','generic_model_only_v23620,\n                    generic_exact_v23620' in c),
('n11 recovery preserved','V23.62.30 N11 TIMEOUT SELECTOR RECOVERY' in c),
('idefix v236232 preserved','V23.62.32 IDEFIX ZERO-RESULT EARLY EXIT' in c),
('pazarama preserved','V23.62.31 PAZARAMA SELECTOR FAST PATH' in c),
('trendyol preserved','V23.62.29 TRENDYOL SELECTOR FAST PATH' in c),
('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
('write guard preserved','DB WRITE GUARD' in (root/'BASLAT_V23_62_33.bat').read_text(encoding='utf-8')),
]
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('FAILED: '+', '.join(failed))
