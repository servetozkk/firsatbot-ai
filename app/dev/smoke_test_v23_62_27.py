from pathlib import Path

r=Path(__file__).resolve().parents[2]
c=(r/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(r/'main.py').read_text(encoding='utf-8')
checks=[
('VERSION',(r/'VERSION').read_text(encoding='utf-8').strip()=='23.62.27'),
('runtime v236227','/api/runtime-identity/v236227' in m),
('force response metadata','"runtime_version": "23.62.27",\n            "test_only": True' in m),
('vatan budget marker','V23.62.27 VATAN SELECTOR-READY LATENCY BUDGET' in c),
('vatan commit navigation','{"n11", "mediamarkt", "teknosa", "vatan"}' in c),
('vatan product-container selector',".product-list a[href$='.html'], .product-item a[href$='.html']" in c),
('vatan fast path marker','V23.62.27 VATAN SELECTOR FAST PATH' in c),
('vatan fast settle','150 if selector_fast_path_v236227 else settle_timeout' in c),
('vatan skip networkidle','if selector_fast_path_v236227:' in c and 'network_elapsed_v23628 = 0.0' in c),
('n11 preserved','V23.62.26 N11 SELECTOR FAST PATH' in c),
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
if failed: raise SystemExit('V23.62.27 smoke failed: '+', '.join(failed))
