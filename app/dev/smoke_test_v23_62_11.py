from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
s=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(s); ast.parse(m)
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.11"),
("search phase","V23.62.11 N11 BINDING PHASE search=" in s),
("scrape phase","V23.62.11 N11 BINDING PHASE scrape_detail=" in s),
("match phase","V23.62.11 N11 BINDING PHASE canonical_match=" in s),
("attach phase","V23.62.11 N11 BINDING PHASE attach_save=" in s),
("total phase","V23.62.11 N11 BINDING TOTAL=" in s),
("v236210 query preserved","V23.62.10 N11 QUERY ORDER" in (r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")),
("force endpoint preserved","/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
("runtime","/api/runtime-identity/v236211" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
