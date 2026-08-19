from pathlib import Path

r=Path(__file__).resolve().parents[2]
c=(r/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(r/'main.py').read_text(encoding='utf-8')
checks=[
('VERSION',(r/'VERSION').read_text(encoding='utf-8').strip()=='23.62.28'),
('runtime v236228','/api/runtime-identity/v236228' in m),
('force response metadata','"runtime_version": "23.62.28",\n            "test_only": True' in m),
('n11 variance marker','V23.62.28 N11 FIRST-QUERY VARIANCE GUARD' in c),
('n11 first query only','query_index == 1' in c and 'len(query_variants) > 1' in c),
('n11 4500 budget','4_500 if n11_first_query_variance_guard_v236228 else navigation_timeout' in c),
('n11 fallback via continue','V23.62.21 N11 SEARCH TIMEOUT' in c and 'continue' in c),
('n11 selector fast path preserved','V23.62.26 N11 SELECTOR FAST PATH' in c),
('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
('idefix preserved','V23.62.24 IDEFIX STRONG-QUERY-ONLY' in c),
('teknosa preserved','V23.62.23 TEKNOSA SELECTOR-READY' in c),
('mediamarkt preserved','V23.62.22 MEDIAMARKT SELECTOR-READY' in c),
('hb preserved','V23.62.20 HB SEARCH LATENCY BUDGET' in c),
('live integrity preserved','runtime-db-integrity-live/v236219' in m),
('write guard preserved','runtime-db-write-guard/v236217' in m),
]
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('V23.62.28 smoke failed: '+', '.join(failed))
