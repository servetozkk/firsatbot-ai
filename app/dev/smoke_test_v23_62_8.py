from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
g=(r/"app/scrapers/generic_store.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(g); ast.parse(m)
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.62.8"),
("n11 budget branch",'if definition.code == "n11":' in c),
("nav 12s","navigation_timeout = 12_000" in c),
("settle 700","settle_timeout = 700" in c),
("one scroll","scroll_count = 1" in c),
("network 1200","network_timeout = 1_200" in c),
("phase telemetry","V23.62.8 N11 SEARCH PHASE" in c),
("total telemetry","V23.62.8 N11 SEARCH TOTAL" in c),
("detail budget preserved","V23.62.7 DETAIL HTTP" in g),
("n11 order preserved","V23.62.6 DETAIL ORDER" in c),
("amazon preserved","V23.62.5 AMAZON VERIFIED AUDIO SEARCH-CARD OFFER" in (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")),
("runtime","/api/runtime-identity/v23628" in m),
("v23627 preserved","/api/runtime-identity/v23627" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
