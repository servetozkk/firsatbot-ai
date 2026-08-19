from pathlib import Path

root = Path(__file__).resolve().parents[2]
main = (root / "main.py").read_text(encoding="utf-8")
generic = (root / "app/scrapers/generic_store.py").read_text(encoding="utf-8")
repair = (root / "app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
cross = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
bat = (root / "BASLAT_V23_62_61.bat").read_bytes()
force = main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]
checks = [
    ("VERSION", (root / "VERSION").read_text().strip() == "23.62.61"),
    ("runtime v236261", '/api/runtime-identity/v236261' in main),
    ("soak v236261", '/api/runtime-soak-stability/v236261' in main),
    ("single source v236261", '_RUNTIME_VERSION_V236261 = "23.62.61"' in main),
    ("force uses v236261", '"runtime_version": _RUNTIME_VERSION_V236261' in force),
    ("runtime source v236261", 'single-source-v236261' in main),
    ("n11 inclusion marker", 'V23.62.61 N11 DEDICATED-LANE INCLUSION INVARIANT' in cross),
    ("user ingestion only", 'self.workload_class == "USER_INGESTION"' in cross),
    ("source n11 only", 'str(source_store_code or "").casefold() == "n11"' in cross),
    ("n11 reinsert", 'definitions.append(n11_definition_v236261)' in cross),
    ("store count preserved", 'original_store_target_v236261' in cross and 'definitions = kept_v236261[:original_store_target_v236261]' in cross),
    ("lowest non n11 drop", 'reversed(definitions) if definition.code != "n11"' in cross),
    ("process shared session preserved", '_N11_DETAIL_SESSION_V236260' in generic),
    ("process shared counter preserved", '_N11_DETAIL_SESSION_REQUEST_COUNT_V236260' in generic),
    ("connection telemetry v236260 preserved", 'V23.62.60 N11 DETAIL HTTP CONNECTION' in generic),
    ("n11 detail 4.5 preserved", 'request_timeout_v23627 = 4.5' in generic),
    ("4500 preserved", '(4_500 if n11_strong_first_budget_v236234 else 4_500)' in cross),
    ("350 recovery preserved", 'V23.62.30 N11 TIMEOUT SELECTOR RECOVERY' in cross and 'timeout=350' in cross),
    ("v2350 recovery preserved", 'V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
    ("v2353 wiring preserved", 'V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
    ("security bypass disabled", '"security_challenge_bypass": "disabled"' in main),
    ("price integrity preserved", '"price_integrity_quarantine": "preserved"' in main),
    ("force user ingestion preserved", 'workload_class="USER_INGESTION"' in force),
    ("bat no utf8 bom", not bat.startswith(b"\xef\xbb\xbf")),
]
failed=[]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit("V23.62.61 smoke FAIL: " + ", ".join(failed))
print(f"V23.62.61 smoke OK {len(checks)}/{len(checks)}")
