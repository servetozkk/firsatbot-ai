from pathlib import Path

root = Path(__file__).resolve().parents[2]
main = (root / "main.py").read_text(encoding="utf-8")
cross = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
generic = (root / "app/scrapers/generic_store.py").read_text(encoding="utf-8")
version = (root / "VERSION").read_text(encoding="utf-8").strip()
force_start = main.index("def force_deep_refresh_v23629")
force_end = main.index('@app.get("/api/runtime-force-refresh-guard/v236225")', force_start)
force = main[force_start:force_end]
checks = [
    ("VERSION", version == "23.62.46"),
    ("runtime v236246", "/api/runtime-identity/v236246" in main),
    ("single source", '_RUNTIME_VERSION_V236246 = "23.62.46"' in main),
    ("force uses v236246", '"runtime_version": _RUNTIME_VERSION_V236246' in force),
    ("runtime source v236246", '"runtime_version_source": "single-source-v236246"' in main),
    ("n11 strong 4250", '(4_250 if n11_strong_first_budget_v236234 else 4_500)' in cross),
    ("n11 4250 marker", 'V23.62.46 N11 STRONG-FIRST HYSTERESIS DEADBAND' in cross),
    ("n11 weak 4500 preserved", 'else 4_500' in cross),
    ("n11 detail http 4.5 preserved", 'request_timeout_v23627 = 4.5' in generic),
    ("n11 browser challenge fail-fast marker", 'V23.62.46 N11 DETAIL BROWSER CHALLENGE FAIL-FAST' in generic),
    ("n11 challenge recheck 0.5", '0.5 if n11_detail_fast_fallback_v236239' in generic),
    ("pazarama 3s preserved", '3.0 if self.config.code == "pazarama"' in generic),
    ("hb selector fast path preserved", 'V23.62.45 HB SELECTOR FAST PATH' in cross),
    ("security bypass disabled metadata", '"security_challenge_bypass": "disabled"' in main),
    ("itopya preserved", 'V23.62.38 ITOPYA BOUNDED BROWSER FALLBACK' in cross),
    ("idefix preserved", 'V23.62.36 IDEFIX BOUNDED SEARCH BUDGET' in cross),
]
failed = []
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
    if not ok:
        failed.append(name)
if failed:
    raise SystemExit("smoke failed: " + ", ".join(failed))
