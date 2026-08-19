from pathlib import Path
import ast

r=Path(__file__).resolve().parents[2]
h=(r/"app/scrapers/hepsiburada.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(h); ast.parse(m)

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.13"),
("perf counter","from time import perf_counter" in h),
("challenge 1+2","enumerate((1_000, 2_000), start=1)" in h),
("settle 1s","page.wait_for_timeout(1_000)" in h),
("launch telemetry","V23.62.13 HB PHASE browser_launch=" in h),
("goto telemetry","V23.62.13 HB PHASE goto=" in h),
("settle telemetry","V23.62.13 HB PHASE settle=" in h),
("challenge telemetry","V23.62.13 HB PHASE challenge_recheck=" in h),
("total telemetry","V23.62.13 HB TOTAL=" in h),
("security fail closed","raise HepsiburadaSecurityChallenge" in h),
("runtime","/api/runtime-identity/v236213" in m),
("n11 timing preserved","/api/runtime-identity/v236212" in m),
("force endpoint preserved","/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
