from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
m=(r/"main.py").read_text(encoding="utf-8")
db=(r/"app/database/database.py").read_text(encoding="utf-8")
c=(r/"app/ops/data_continuity_v219.py").read_text(encoding="utf-8")
ast.parse(m); ast.parse(db); ast.parse(c)
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.18"),
("live endpoint","/api/runtime-db-integrity-live/v236218" in m),
("quick check","PRAGMA quick_check(1)" in m),
("full check","PRAGMA integrity_check" in m),
("read only mode","mode=ro" in m),
("runtime identity","/api/runtime-identity/v236218" in m),
("write guard preserved","class SafeSQLiteSessionV23617" in db),
("continuity full integrity","FAILED_FULL_INTEGRITY_CHECK" in c),
("force endpoint preserved","/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
