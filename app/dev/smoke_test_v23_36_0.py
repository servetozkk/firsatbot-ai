from pathlib import Path
r=Path(__file__).resolve().parents[2]
repair=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.36.0"),
("undefined rejection removed","rejection_reasons.append(reason)" not in repair),
("v23.35 uses errors","V23.35 DETAIL COLOR GATE" in repair and "errors.append(reason)" in repair),
("post scrape gate","V23.36 POST-SCRAPE COLOR GATE" in repair),
("pre persistence",repair.index("V23.36 POST-SCRAPE COLOR GATE") < repair.index("attached = force_attach_candidate_offer(", repair.index("V23.36 POST-SCRAPE COLOR GATE"))),
("final candidate authority","post_candidate_color = _generic_explicit_color_v2334(candidate)" in repair),
("runtime","/api/runtime-identity/v2336" in main),
("v2335 preserved","/api/runtime-identity/v2335" in main),
("v2334 preserved","/api/runtime-identity/v2334" in main),
("v2333 preserved","/api/runtime-identity/v2333" in main),
("v2330 preserved","/api/runtime-identity/v2330" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
