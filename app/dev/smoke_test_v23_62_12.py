from pathlib import Path
import ast

r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(m)

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.12"),
("completion map","n11_completed_at_v236212 = {}" in c),
("done callback","future.add_done_callback(_capture_n11_done_v236212)" in c),
("actual finish lookup","n11_completed_at_v236212.get(" in c),
("collection lag","collection_lag_v236212" in c),
("timing log","V23.62.12 N11 DEDICATED TIMING" in c),
("binding telemetry preserved","V23.62.11 N11 BINDING TOTAL=" in (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")),
("query order preserved","V23.62.10 N11 QUERY ORDER" in c),
("force endpoint preserved","/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
("runtime","/api/runtime-identity/v236212" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
