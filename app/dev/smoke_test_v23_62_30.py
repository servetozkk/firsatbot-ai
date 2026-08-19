from pathlib import Path

root = Path(__file__).resolve().parents[2]
c = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m = (root / "main.py").read_text(encoding="utf-8")
checks = [
    ("VERSION", (root / "VERSION").read_text(encoding="utf-8").strip() == "23.62.30"),
    ("runtime v236230", "/api/runtime-identity/v236230" in m),
    ("force response metadata", '"runtime_version": "23.62.30"' in m),
    ("n11 recovery marker", "V23.62.30 N11 TIMEOUT SELECTOR RECOVERY" in c),
    ("n11 recovery only first guard", "if n11_first_query_variance_guard_v236228:" in c),
    ("n11 recovery probe 350", 'timeout=350' in c),
    ("n11 recovery settle 150", 'page.wait_for_timeout(150)' in c),
    ("n11 recovery product selector", 'a[href*=\'/urun/\']' in c or 'a[href*="/urun/"]' in c),
    ("n11 fail closed fallback", "if not n11_timeout_selector_recovered_v236230:" in c and "continue" in c),
    ("trendyol preserved", "V23.62.29 TRENDYOL SELECTOR FAST PATH" in c),
    ("n11 variance preserved", "V23.62.28 N11 FIRST-QUERY VARIANCE GUARD" in c),
    ("vatan preserved", "V23.62.27 VATAN SELECTOR FAST PATH" in c),
    ("n11 selector fast path preserved", "V23.62.26 N11 SELECTOR FAST PATH" in c),
    ("single flight preserved", "FORCE_REFRESH_ALREADY_RUNNING" in m),
    ("429 cooldown preserved", "FORCE_REFRESH_COOLDOWN" in m),
    ("write guard preserved", "runtime-db-write-guard/v236217" in m),
]
failed=[]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit("Smoke failed: " + ", ".join(failed))
