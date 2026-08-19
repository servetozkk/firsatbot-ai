from pathlib import Path

root = Path(__file__).resolve().parents[2]
main = (root / "main.py").read_text(encoding="utf-8")
generic = (root / "app/scrapers/generic_store.py").read_text(encoding="utf-8")
repair = (root / "app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
cross = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
bat = (root / "BASLAT_V23_62_59.bat").read_bytes()
checks = [
    ("VERSION", (root / "VERSION").read_text().strip() == "23.62.59"),
    ("runtime v236259", '/api/runtime-identity/v236259' in main),
    ("soak v236259", '/api/runtime-soak-stability/v236259' in main),
    ("single source v236259", '_RUNTIME_VERSION_V236259 = "23.62.59"' in main),
    ("force uses v236259", '"runtime_version": _RUNTIME_VERSION_V236259' in main),
    ("runtime source v236259", 'single-source-v236259' in main),
    ("persistent session field", '_n11_detail_session_v236259' in generic),
    ("persistent session count", '_n11_detail_session_request_count_v236259' in generic),
    ("connection telemetry", 'V23.62.59 N11 DETAIL HTTP CONNECTION' in generic),
    ("n11 session not closed", 'if self.config.code != "n11":\n                session.close()' in generic),
    ("pool size 2", 'pool_maxsize=2 if self.config.code == "n11" else 10' in generic),
    ("n11 detail 4.5 preserved", 'request_timeout_v23627 = 4.5' in generic),
    ("4500 preserved", '(4_500 if n11_strong_first_budget_v236234 else 4_500)' in cross),
    ("350 recovery preserved", 'V23.62.30 N11 TIMEOUT SELECTOR RECOVERY' in cross and 'timeout=350' in cross),
    ("v2350 recovery preserved", 'V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
    ("v2353 wiring preserved", 'V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
    ("browser startup telemetry preserved", 'V23.62.57 N11 BROWSER STARTUP' in cross),
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
    raise SystemExit("V23.62.59 smoke FAIL: " + ", ".join(failed))
print(f"V23.62.59 smoke OK {len(checks)}/{len(checks)}")
