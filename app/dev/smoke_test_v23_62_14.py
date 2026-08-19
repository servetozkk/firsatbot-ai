from pathlib import Path
import ast

r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(m)

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.14"),
("selector telemetry","V23.62.14 HB SELECTOR [" in c),
("early stop","V23.62.14 HB SELECTOR EARLY STOP" in c),
("threshold 8","if len(current_candidates) >= 8:" in c),
("raw dedupe","V23.62.14 HB RAW DEDUPE" in c),
("clean url dedupe","seen_urls_v236214" in c),
("search total","V23.62.14 HB SEARCH TOTAL" in c),
("hb challenge preserved","V23.62.13 HB PHASE challenge_recheck=" in (r/"app/scrapers/hepsiburada.py").read_text(encoding="utf-8")),
("n11 timing preserved","V23.62.12 N11 DEDICATED TIMING" in c),
("force endpoint preserved","/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
("runtime","/api/runtime-identity/v236214" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
