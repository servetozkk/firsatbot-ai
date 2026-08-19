from pathlib import Path
import ast

r = Path(__file__).resolve().parents[2]
c = (r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m = (r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(m)

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.20"),
    ("hb budget branch", 'elif definition.code == "hepsiburada":' in c),
    ("hb nav 10s", "navigation_timeout = 10_000" in c),
    ("hb settle 650", "settle_timeout = 650" in c),
    ("hb no scroll", "scroll_count = 0" in c),
    ("hb network 650", "network_timeout = 650" in c),
    ("hb phase telemetry", "V23.62.20 HB SEARCH PHASE" in c),
    ("hb timeout telemetry", "V23.62.20 HB SEARCH TIMEOUT" in c),
    ("hb selector optimization preserved", "V23.62.14 HB SELECTOR EARLY STOP" in c),
    ("hb challenge preserved", "V23.62.13 HB PHASE challenge_recheck=" in (r/"app/scrapers/hepsiburada.py").read_text(encoding="utf-8")),
    ("live db endpoint preserved", "/api/runtime-db-integrity-live/v236219" in m),
    ("write guard endpoint preserved", "/api/runtime-db-write-guard/v236217" in m),
    ("force endpoint preserved", "/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
    ("runtime", "/api/runtime-identity/v236220" in m),
]

for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)

raise SystemExit(0 if all(ok for _, ok in checks) else 1)
