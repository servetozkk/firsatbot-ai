from pathlib import Path
import ast

r=Path(__file__).resolve().parents[2]
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(s)
ast.parse(m)

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.1"),
("source passed to discovery","source_product=source_product" in s),
("candidate helper","def _candidate_color_priority_v23621" in s),
("white aliases","ceramic white" in s and "seramik beyaz" in s),
("detail ordering","COLOR-AWARE DETAIL ORDER" in s),
("sort uses color priority","self._candidate_color_priority_v23621(" in s),
("same-product gate preserved","self._is_same_product(" in s),
("variant gate preserved","validate_variant(" in s),
("runtime","/api/runtime-identity/v23621" in m),
("v23620 preserved","/api/runtime-identity/v23620" in m),
]
for name,ok in checks:
    print(("OK  " if ok else "FAIL ")+name)
raise SystemExit(0 if all(ok for _,ok in checks) else 1)
