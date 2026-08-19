from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
o=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.19.0"),
("brand gate","V23.19 generic kesin red" in s),
("verified card helper","_v2319_verified_search_card_offer" in o),
("challenge policy","SECURITY_CHALLENGE" in o),
("single-price gate","len(prices) != 1" in o),
("price integrity attach","force_attach_candidate_offer" in o),
("v2318 preserved","_v2318_generic_safe_fallback_product" in o),
("runtime","/api/runtime-identity/v2319" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
