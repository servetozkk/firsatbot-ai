from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(root/'main.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.36'),
 ('runtime v236236','/api/runtime-identity/v236236' in m),
 ('force response metadata','"runtime_version": "23.62.36"' in m),
 ('idefix 5500 budget','idefix_navigation_budget_v236236 = 5_500' in c),
 ('idefix bounded marker','V23.62.36 IDEFIX BOUNDED SEARCH BUDGET' in c),
 ('idefix anchor probe','V23.62.36 IDEFIX ANCHOR PROBE' in c),
 ('idefix fail closed','V23.62.36 IDEFIX FAIL-CLOSED NO-CANDIDATE' in c),
 ('idefix timeout telemetry','V23.62.36 IDEFIX SEARCH TIMEOUT' in c),
 ('idefix max anchor 1500','min(1_500, idefix_remaining_ms_v236236)' in c),
 ('old zero probe retired','for _idefix_probe_v236232 in range(8)' not in c),
 ('strong query preserved','V23.62.24 IDEFIX STRONG-QUERY-ONLY' in c),
 ('n11 scope hotfix preserved','n11_strong_brand_model_v236235 = bool(' in c),
 ('n11 6500 preserved','6_500 if n11_strong_first_budget_v236234 else 4_500' in c),
 ('pazarama preserved','V23.62.31 PAZARAMA SELECTOR FAST PATH' in c),
 ('trendyol preserved','V23.62.29 TRENDYOL SELECTOR FAST PATH' in c),
 ('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
 ('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
 ('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: raise SystemExit(1)
