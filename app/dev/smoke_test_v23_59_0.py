from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
http_start=c.index("def _http_first_candidate_urls_v2350")
http_gate=c.index("raw_bundle_reason_v2359 = _search_card_bundle_pre_filter_reason_v2356(", http_start)
http_score=c.index("score, reason = _search_result_candidate_score(", http_start)
last_gate=c.rfind("raw_bundle_reason_v2359 = _search_card_bundle_pre_filter_reason_v2356(")
last_score=c.rfind("score, reason = _search_result_candidate_score(")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.59.0"),
("early event","V23.59 EARLY BUNDLE PREFILTER REJECT" in c),
("two early gates",c.count("raw_bundle_reason_v2359 = _search_card_bundle_pre_filter_reason_v2356(")>=2),
("http-first gate before score",http_gate < http_score),
("browser gate before score",last_gate < last_score),
("telemetry preserved","bundle_prefilter_reject_count" in c),
("v2358 event preserved","V23.58 BUNDLE PREFILTER REJECT" in c),
("runtime","/api/runtime-identity/v2359" in m),
("v2358 runtime preserved","/api/runtime-identity/v2358" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
