from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(m)
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.22"),
("mm commit",'definition.code in {"n11", "mediamarkt"}' in c),
("mm selector","/tr/product/" in c and "timeout=6_000" in c),
("mm budget","V23.62.22 MEDIAMARKT SELECTOR-READY LATENCY BUDGET" in c),
("mm telemetry","V23.62.22 MEDIAMARKT SEARCH PHASE" in c),
("n11 preserved","V23.62.21 N11 SEARCH PHASE" in c),
("hb preserved","V23.62.20 HB SEARCH PHASE" in c),
("live db preserved","/api/runtime-db-integrity-live/v236219" in m),
("write guard preserved","/api/runtime-db-write-guard/v236217" in m),
("force preserved","/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
("runtime","/api/runtime-identity/v236222" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
