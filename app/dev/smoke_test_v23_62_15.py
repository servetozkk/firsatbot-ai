from pathlib import Path
import ast

r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(m)

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.15"),
("idefix cap branch",'if definition.code == "idefix":' in c),
("two query cap","capped_v236215 = queries[:2]" in c),
("cap telemetry","V23.62.15 IDEFIX QUERY CAP" in c),
("search telemetry","V23.62.15 IDEFIX SEARCH TOTAL" in c),
("hb selector preserved","V23.62.14 HB SELECTOR EARLY STOP" in c),
("hb challenge preserved","V23.62.13 HB PHASE challenge_recheck=" in (r/"app/scrapers/hepsiburada.py").read_text(encoding="utf-8")),
("n11 timing preserved","V23.62.12 N11 DEDICATED TIMING" in c),
("force endpoint preserved","/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
("runtime","/api/runtime-identity/v236215" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
