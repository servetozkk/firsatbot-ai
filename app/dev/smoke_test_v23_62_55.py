from pathlib import Path

root = Path(__file__).resolve().parents[2]
main = (root / "main.py").read_text(encoding="utf-8")
cross = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
repair = (root / "app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
version = (root / "VERSION").read_text(encoding="utf-8").strip()
checks = [
    ("VERSION", version == "23.62.55"),
    ("runtime v236255", "/api/runtime-identity/v236255" in main),
    ("soak v236255", "/api/runtime-soak-stability/v236255" in main),
    ("single source", '_RUNTIME_VERSION_V236255 = "23.62.55"' in main),
    ("force uses v236255", '"runtime_version": _RUNTIME_VERSION_V236255' in main),
    ("runtime source fixed", 'single-source-v236255' in main),
    ("ledger metadata", 'v23.62.55-per-query-ledger-query-recovery-cleanup-postprocess-find-total' in main),
    ("query timing marker", 'V23.62.55 N11 QUERY TIMING' in cross),
    ("query ledger marker", 'V23.62.55 N11 QUERY LEDGER' in cross),
    ("breakdown marker", 'V23.62.55 N11 SEARCH PHASE BREAKDOWN' in cross),
    ("recovery total", 'n11_recovery_total_v236255' in cross),
    ("query ledger", 'n11_query_ledger_v236255' in cross),
    ("4500 preserved", '4_500 if n11_strong_first_budget_v236234 else 4_500' in cross),
    ("350 preserved", 'timeout=350' in cross),
    ("v2350 recovery preserved", 'V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
    ("v2353 wiring preserved", 'V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
    ("security bypass disabled", 'security_challenge_bypass": "disabled"' in main),
    ("price integrity preserved", 'price_integrity_quarantine": "preserved"' in main),
    ("production unchanged", 'production_ingestion_behavior": "unchanged"' in main),
]
failed=[name for name,ok in checks if not ok]
for name,ok in checks:
    print(("OK  " if ok else "FAIL ")+name)
if failed:
    raise SystemExit("V23.62.55 smoke failed: "+", ".join(failed))
print(f"V23.62.55 smoke OK {len(checks)}/{len(checks)}")
