from pathlib import Path
import ast

r = Path(__file__).resolve().parents[2]
g = (r/"app/scrapers/generic_store.py").read_text(encoding="utf-8")
m = (r/"main.py").read_text(encoding="utf-8")
c = (r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")

ast.parse(g)
ast.parse(m)
ast.parse(c)

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip() == "23.62.7"),
    ("perf counter", "from time import perf_counter" in g),
    ("n11 timeout 8", 'request_timeout_v23627 = 8' in g),
    ("n11 retry zero", 'if self.config.code == "n11"' in g and 'total=0' in g),
    ("other stores 35", 'request_timeout_v23627 = 35' in g),
    ("http telemetry", "V23.62.7 DETAIL HTTP [" in g),
    ("http fallback telemetry", "V23.62.7 DETAIL HTTP FALLBACK" in g),
    ("browser telemetry", "V23.62.7 DETAIL BROWSER" in g),
    ("n11 ordering preserved", "V23.62.6 DETAIL ORDER" in c),
    ("n11 single-card preserved", "_n11_single_card_price_priority_v23626" in c),
    ("amazon preserved", "V23.62.5 AMAZON VERIFIED AUDIO SEARCH-CARD OFFER" in (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")),
    ("runtime", "/api/runtime-identity/v23627" in m),
    ("v23626 preserved", "/api/runtime-identity/v23626" in m),
]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
raise SystemExit(0 if all(ok for _, ok in checks) else 1)
