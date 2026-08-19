from pathlib import Path
import ast

r = Path(__file__).resolve().parents[2]
m = (r/"main.py").read_text(encoding="utf-8")
c = (r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
g = (r/"app/scrapers/generic_store.py").read_text(encoding="utf-8")
s = (r/"app/services/smart_catalog_refresh_v218_service.py").read_text(encoding="utf-8")
ast.parse(m); ast.parse(c); ast.parse(g); ast.parse(s)

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.9"),
    ("runtime", "/api/runtime-identity/v23629" in m),
    ("force endpoint", "/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
    ("localhost gate", 'client_host not in {"127.0.0.1", "::1", "localhost"}' in m),
    ("force true", "force=True" in m),
    ("user workload", 'workload_class="USER_INGESTION"' in m),
    ("telemetry adapter", "_deep_refresh_store_telemetry_v2347" in m),
    ("backoff force support", "elif force or next_check is None or next_check <= now" in s),
    ("n11 search v23628 preserved", "V23.62.8 N11 SEARCH PHASE" in c),
    ("n11 detail v23627 preserved", "V23.62.7 DETAIL HTTP" in g),
    ("n11 order v23626 preserved", "V23.62.6 DETAIL ORDER" in c),
    ("amazon v23625 preserved", "V23.62.5 AMAZON VERIFIED AUDIO SEARCH-CARD OFFER" in (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")),
]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
raise SystemExit(0 if all(ok for _,ok in checks) else 1)
