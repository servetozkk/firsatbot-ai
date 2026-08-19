from pathlib import Path
import ast

r = Path(__file__).resolve().parents[2]
c = (r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m = (r/"main.py").read_text(encoding="utf-8")
ast.parse(c)
ast.parse(m)

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip() == "23.62.21"),
    ("n11 commit", 'wait_until=("commit" if definition.code == "n11" else "domcontentloaded")' in c),
    ("n11 product selector", "first.wait_for(" in c and "/urun/" in c),
    ("selector timeout", "timeout=6_000" in c),
    ("n11 no scroll", "scroll_count = 0" in c),
    ("n11 settle 350", "settle_timeout = 350" in c),
    ("n11 network 300", "network_timeout = 300" in c),
    ("n11 phase telemetry", "V23.62.21 N11 SEARCH PHASE" in c),
    ("hb v236220 preserved", "V23.62.20 HB SEARCH LATENCY BUDGET" in c),
    ("live db preserved", "/api/runtime-db-integrity-live/v236219" in m),
    ("write guard preserved", "/api/runtime-db-write-guard/v236217" in m),
    ("force endpoint preserved", "/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
    ("runtime", "/api/runtime-identity/v236221" in m),
]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)

raise SystemExit(0 if all(ok for _, ok in checks) else 1)
