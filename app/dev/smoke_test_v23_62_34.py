from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(root/'main.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.34'),
 ('runtime v236234','/api/runtime-identity/v236234' in m),
 ('force response metadata','\"runtime_version\": \"23.62.34\"' in m),
 ('adaptive budget marker','V23.62.34 N11 ADAPTIVE FIRST-QUERY BUDGET' in c),
 ('strong first 6500','6_500 if n11_strong_first_budget_v236234 else 4_500' in c),
 ('strong query order preserved','n11_strong_brand_model_v236233' in c and 'V23.62.33 N11 QUERY ORDER' in c),
 ('weak 4500 preserved','else 4_500' in c),
 ('subsequent full budget preserved','else navigation_timeout' in c),
 ('n11 recovery preserved','V23.62.30 N11 TIMEOUT SELECTOR RECOVERY' in c),
 ('idefix preserved','V23.62.32 IDEFIX' in c),
 ('pazarama preserved','V23.62.31 PAZARAMA' in c),
 ('trendyol preserved','V23.62.29 TRENDYOL' in c),
 ('vatan preserved','V23.62.27 VATAN' in c),
 ('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
 ('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
]
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('FAILED: '+', '.join(failed))
