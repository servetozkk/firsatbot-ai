from pathlib import Path

root = Path(__file__).resolve().parents[2]
main = (root / "main.py").read_text(encoding="utf-8")
cross = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
generic = (root / "app/scrapers/generic_store.py").read_text(encoding="utf-8")
hb = (root / "app/scrapers/hepsiburada.py").read_text(encoding="utf-8")
version = (root / "VERSION").read_text(encoding="utf-8").strip()
force_start = main.index("def force_deep_refresh_v23629")
force_end = main.index('@app.get("/api/runtime-force-refresh-guard/v236225")', force_start)
force = main[force_start:force_end]
endpoint_start = main.index('@app.get("/api/runtime-identity/v236248")')
endpoint = main[endpoint_start:]
checks = [
    ("VERSION", version == "23.62.48"),
    ("runtime v236248", "/api/runtime-identity/v236248" in main),
    ("soak endpoint", "/api/runtime-soak-stability/v236248" in main),
    ("single source", '_RUNTIME_VERSION_V236248 = "23.62.48"' in main),
    ("force uses v236248", '"runtime_version": _RUNTIME_VERSION_V236248' in force),
    ("force records soak", "_record_soak_run_v236248(" in force),
    ("rolling max 50", "_SOAK_V236248_MAX_RUNS = 50" in main),
    ("observation only metadata", '"behavior_policy": "v23.62.47-production-baseline-preserved-no-scraping-tweak"' in endpoint),
    ("regression offer 6", "_SOAK_V236248_EXPECTED_OFFERS = 6" in main),
    ("regression success 6", "_SOAK_V236248_EXPECTED_SUCCESS_STORES = 6" in main),
    ("n11 strong 4250 locked", '(4_250 if n11_strong_first_budget_v236234 else 4_500)' in cross),
    ("n11 weak 4500 locked", 'else 4_500' in cross),
    ("n11 detail http 4.5 locked", 'request_timeout_v23627 = 4.5' in generic),
    ("n11 browser challenge 0.5 locked", '0.5 if n11_detail_fast_fallback_v236239' in generic),
    ("hb selector fast path locked", 'V23.62.45 HB SELECTOR FAST PATH' in cross),
    ("hb one second recheck locked", "for attempt, wait_ms in enumerate((1_000,), start=1):" in hb),
    ("itopya bounded locked", 'V23.62.38 ITOPYA BOUNDED BROWSER FALLBACK' in cross),
    ("idefix bounded locked", 'V23.62.36 IDEFIX BOUNDED SEARCH BUDGET' in cross),
    ("security bypass disabled", '"security_challenge_bypass": "disabled"' in endpoint),
    ("price integrity preserved", '"price_integrity_quarantine": "preserved"' in endpoint),
    ("production ingestion unchanged", '"production_ingestion_behavior": "unchanged"' in endpoint),
]
failed=[]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit("smoke failed: " + ", ".join(failed))
