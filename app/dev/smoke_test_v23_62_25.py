from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
m=(r/"main.py").read_text(encoding="utf-8")
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
ast.parse(m); ast.parse(c)
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.25"),
("single flight lock","_FORCE_REFRESH_V236225_LOCK" in m),
("nonblocking acquire","acquire(blocking=False)" in m),
("409 active","FORCE_REFRESH_ALREADY_RUNNING" in m),
("cooldown","_FORCE_REFRESH_V236225_COOLDOWN_SECONDS = 5.0" in m),
("429 cooldown","FORCE_REFRESH_COOLDOWN" in m),
("guard state endpoint","/api/runtime-force-refresh-guard/v236225" in m),
("runtime","/api/runtime-identity/v236225" in m),
("force endpoint preserved","/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
("idefix preserved","V23.62.24 IDEFIX STRONG-QUERY-ONLY" in c),
("teknosa preserved","V23.62.23 TEKNOSA SEARCH PHASE" in c),
("mediamarkt preserved","V23.62.22 MEDIAMARKT SEARCH PHASE" in c),
("n11 preserved","V23.62.21 N11 SEARCH PHASE" in c),
("hb preserved","V23.62.20 HB SEARCH PHASE" in c),
("live integrity preserved","/api/runtime-db-integrity-live/v236219" in m),
("write guard preserved","/api/runtime-db-write-guard/v236217" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
