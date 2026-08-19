from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(root/'main.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.37'),
 ('runtime v236237','/api/runtime-identity/v236237' in m),
 ('force response metadata','"runtime_version": "23.62.37"' in m),
 ('early fallback marker','V23.62.37 N11 STRONG-FIRST EARLY-FALLBACK' in c),
 ('strong first 3250','(3_250 if n11_strong_first_budget_v236234 else 4_500)' in c),
 ('weak 4500 preserved','else 4_500' in c),
 ('query order preserved','V23.62.33 N11 QUERY ORDER' in c),
 ('scope hotfix preserved','n11_strong_brand_model_v236235' in c),
 ('idefix v236236 preserved','V23.62.36 IDEFIX BOUNDED SEARCH BUDGET' in c),
 ('pazarama preserved','V23.62.31 PAZARAMA SELECTOR FAST PATH' in c),
 ('trendyol preserved','V23.62.29 TRENDYOL SELECTOR FAST PATH' in c),
 ('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
 ('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
 ('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
]
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('FAILED: '+', '.join(failed))
