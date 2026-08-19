from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
o=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.20.0"),
("price extractor","_extract_dom_card_prices_v2320" in s),
("dom evidence","evidence_source" in s and "dom_card" in s),
("html fallback blocked","html_fallback" in s),
("card prices","card_prices" in s),
("single price verified","len(prices) != 1" in o),
("dom-only verified",'evidence_source") or "") != "dom_card"' in o),
("brand gate preserved","V23.19 generic kesin red" in s),
("runtime","/api/runtime-identity/v2320" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
