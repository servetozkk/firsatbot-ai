from pathlib import Path
import ast

r=Path(__file__).resolve().parents[2]
s_path=r/"app/services/smart_catalog_refresh_v218_service.py"
s=s_path.read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")

tree=ast.parse(s)

# Exact regression: no Name load for `hours` may remain in smart refresh.
hours_loads=[
    node for node in ast.walk(tree)
    if isinstance(node, ast.Name)
    and isinstance(node.ctx, ast.Load)
    and node.id=="hours"
]

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.11"),
("undefined hours removed",len(hours_loads)==0),
("derived backoff variable","backoff_hours_v236111" in s),
("retry seconds is source","float(retry_after_v23611) / 3600.0" in s),
("state uses derived value","'backoff_hours': backoff_hours_v236111" in s),
("runtime","/api/runtime-identity/v236111" in m),
("v236110 preserved","/api/runtime-identity/v236110" in m),
("foreground ready preserved","READ_ONLY_NO_SQLITE_WRITER" in (r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
