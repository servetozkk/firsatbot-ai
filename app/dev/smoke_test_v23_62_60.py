from pathlib import Path

root = Path(__file__).resolve().parents[2]
main = (root / "main.py").read_text(encoding="utf-8")
generic = (root / "app/scrapers/generic_store.py").read_text(encoding="utf-8")
repair = (root / "app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
cross = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
bat = (root / "BASLAT_V23_62_60.bat").read_bytes()
checks = [
    ("VERSION", (root / "VERSION").read_text().strip() == "23.62.60"),
    ("runtime v236260", '/api/runtime-identity/v236260' in main),
    ("soak v236260", '/api/runtime-soak-stability/v236260' in main),
    ("single source v236260", '_RUNTIME_VERSION_V236260 = "23.62.60"' in main),
    ("force uses v236260", '"runtime_version": _RUNTIME_VERSION_V236260' in main),
    ("runtime source v236260", 'single-source-v236260' in main),
    ("process shared session", '_N11_DETAIL_SESSION_V236260' in generic),
    ("process shared counter", '_N11_DETAIL_SESSION_REQUEST_COUNT_V236260' in generic),
    ("process shared lock", '_N11_DETAIL_SESSION_LOCK_V236260' in generic),
    ("shared session helper", '_n11_shared_detail_session_v236260' in generic),
    ("connection telemetry v236260", 'V23.62.60 N11 DETAIL HTTP CONNECTION' in generic),
    ("process scope telemetry", 'scope=process keep_alive=True' in generic),
    ("no instance session v2359", 'self._n11_detail_session_v236259' not in generic),
    ("n11 session not closed", 'if self.config.code != "n11":\n                session.close()' in generic),
    ("pool size 2", 'pool_maxsize=2' in generic),
    ("n11 detail 4.5 preserved", 'request_timeout_v23627 = 4.5' in generic),
    ("4500 preserved", '(4_500 if n11_strong_first_budget_v236234 else 4_500)' in cross),
    ("350 recovery preserved", 'V23.62.30 N11 TIMEOUT SELECTOR RECOVERY' in cross and 'timeout=350' in cross),
    ("v2350 recovery preserved", 'V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
    ("v2353 wiring preserved", 'V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
    ("security bypass disabled", '"security_challenge_bypass": "disabled"' in main),
    ("price integrity preserved", '"price_integrity_quarantine": "preserved"' in main),
    ("production unchanged", '"production_ingestion_behavior": "unchanged"' in main),
    ("bat no utf8 bom", not bat.startswith(b"\xef\xbb\xbf")),
]
failed=[]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit("V23.62.60 smoke FAIL: " + ", ".join(failed))
print(f"V23.62.60 smoke OK {len(checks)}/{len(checks)}")
