from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(s); ast.parse(m)
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.62.2"),
("source helper","def _source_color_v23622" in s),
("card helper","def _candidate_card_color_priority_v23622" in s),
("evidence priority","v23622_color_priority" in s),
("real sort","get(\"v23622_color_priority\",0)" in s),
("observability","V23.62.2 CARD-COLOR DETAIL ORDER" in s),
("variant gate","validate_variant(" in s),
("same-product gate","self._is_same_product(" in s),
("runtime","/api/runtime-identity/v23622" in m),
("v23621 preserved","/api/runtime-identity/v23621" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
