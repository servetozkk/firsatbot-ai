from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=(r/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
c=(r/'app/services/category_aware_matcher_v221.py').read_text(encoding='utf-8')
m=(r/'main.py').read_text(encoding='utf-8')
checks=[
('VERSION',(r/'VERSION').read_text().strip()=='23.31.0'),
('search signatures','_strong_generic_model_signatures_v2331' in s),
('HAF/P/KVC regex','[a-z]{1,5}' in s and 'd{1,5}' in s),
('freebuds se','freebuds\\s+se' in s),
('air purifier','air\\s+purifier' in s),
('thermochef','thermochef\\s+xl' in s),
('fastfryer','fastfryer\\s+xl' in s),
('generic query mode','generic_model_family' in s),
('search candidate bridge','_generic_model_candidate_score_v2331' in s),
('manufacturer code precedence','source_codes' in s and 'üretici model kodu eksik/farklı' in s),
('detail bridge','_generic_model_match_v2331' in c),
('detail route','generic_v2331=_generic_model_match_v2331' in c),
('brand guard','V23.31 generic model kesin red: marka farklı' in c),
('runtime','/api/runtime-identity/v2331' in m),
('v2330 preserved','/api/runtime-identity/v2330' in m),
('price integrity preserved','price_integrity_quarantine' in m),
]
for n,ok in checks: print(('OK  ' if ok else 'FAIL ')+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
