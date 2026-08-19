from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
m=(r/'main.py').read_text(encoding='utf-8')
c=(r/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
ast.parse(m); ast.parse(c)
checks=[
('VERSION',(r/'VERSION').read_text(encoding='utf-8').strip()=='23.62.26'),
('runtime v236226','/api/runtime-identity/v236226' in m),
('force response metadata','"runtime_version": "23.62.26",\n            "test_only": True' in m),
('n11 fast path marker','V23.62.26 N11 SELECTOR FAST PATH' in c),
('n11 fast settle','150 if n11_selector_fast_path_v236226 else settle_timeout' in c),
('n11 skip networkidle','if n11_selector_fast_path_v236226:' in c and 'network_elapsed_v23628 = 0.0' in c),
('n11 fallback preserved','V23.62.21 N11 SEARCH PHASE' in c),
('single flight preserved','_FORCE_REFRESH_V236225_LOCK' in m and 'acquire(blocking=False)' in m),
('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
('idefix preserved','V23.62.24 IDEFIX STRONG-QUERY-ONLY' in c),
('teknosa preserved','V23.62.23 TEKNOSA SEARCH PHASE' in c),
('mediamarkt preserved','V23.62.22 MEDIAMARKT SEARCH PHASE' in c),
('hb preserved','V23.62.20 HB SEARCH PHASE' in c),
('live integrity preserved','/api/runtime-db-integrity-live/v236219' in m),
('write guard preserved','/api/runtime-db-write-guard/v236217' in m),
]
for n,v in checks: print(('OK  ' if v else 'FAIL ')+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
