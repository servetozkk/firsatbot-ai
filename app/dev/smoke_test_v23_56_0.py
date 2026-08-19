from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.56.0"),
("prefilter helper","def _search_card_bundle_pre_filter_reason_v2356" in c),
("prefilter before identity","bundle_reject_v2356" in c and c.index("bundle_reject_v2356") < c.index("identity = _query_identity_tokens(search_query)", c.index("def _search_result_candidate_score"))),
("watch fit marker","watch\\s+fit" in c),
("freebuds marker","freebuds\\s+se" in c),
("v2355 detail guard preserved","def _audio_mixed_main_product_reason_v2355" in m),
("runtime","/api/runtime-identity/v2356" in main),
("v2355 runtime preserved","/api/runtime-identity/v2355" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
