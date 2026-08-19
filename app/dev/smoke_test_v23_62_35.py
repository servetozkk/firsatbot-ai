from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(root/'main.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.35'),
 ('runtime v236235','/api/runtime-identity/v236235' in m),
 ('force response metadata','"runtime_version": "23.62.35"' in m),
 ('scope-safe recompute','n11_strong_brand_model_v236235 = bool(' in c),
 ('scope-safe exact','n11_generic_exact_v236235' in c),
 ('no v233 helper-scope use in adaptive block','and n11_strong_brand_model_v236233\n                        and query_variants' not in c),
 ('strong first 6500','6_500 if n11_strong_first_budget_v236234 else 4_500' in c),
 ('adaptive marker','V23.62.35 N11 ADAPTIVE FIRST-QUERY BUDGET' in c),
 ('query order preserved','V23.62.33 N11 QUERY ORDER' in c),
 ('n11 recovery preserved','V23.62.30 N11 TIMEOUT SELECTOR RECOVERY' in c),
 ('idefix preserved','V23.62.32 IDEFIX ZERO-RESULT EARLY EXIT' in c),
 ('pazarama preserved','V23.62.31 PAZARAMA SELECTOR FAST PATH' in c),
 ('trendyol preserved','V23.62.29 TRENDYOL SELECTOR FAST PATH' in c),
 ('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
 ('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
 ('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: raise SystemExit(1)
