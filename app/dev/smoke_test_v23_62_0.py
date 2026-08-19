from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.0"),
("generic signatures source","identity.get(\"generic_signatures\")" in s),
("generic exact synthesis","generic_exact_v23620" in s),
("model before broad","preferred = [\n                generic_exact_v23620,\n                generic_model_only_v23620,\n                exact" in s),
("observability","V23.62 GENERIC MODEL QUERY SYNTHESIS" in s),
("freebuds signature parser",r"freebuds\s+se" in s),
("runtime","/api/runtime-identity/v23620" in m),
("v236111 preserved","/api/runtime-identity/v236111" in m),
]
ast.parse(s); ast.parse(m)
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
