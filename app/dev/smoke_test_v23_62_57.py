from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
main = (ROOT / "main.py").read_text(encoding="utf-8")
cross = (ROOT / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
repair = (ROOT / "app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
bat_bytes = (ROOT / "BASLAT_V23_62_57.bat").read_bytes()

checks = [
    ("VERSION", version == "23.62.57"),
    ("runtime v236257", "/api/runtime-identity/v236257" in main),
    ("soak v236257", "/api/runtime-soak-stability/v236257" in main),
    ("single source v236257", '_RUNTIME_VERSION_V236257 = "23.62.57"' in main),
    ("force uses v236257", '"runtime_version": _RUNTIME_VERSION_V236257' in main),
    ("runtime source v236257", 'single-source-v236257' in main),
    ("browser startup metadata", 'v23.62.57-launch-plus-new-page-separated' in main),
    ("browser startup timer", 'V23.62.57 N11 BROWSER STARTUP' in cross),
    ("browser startup breakdown", 'browser_startup={n11_browser_startup_v236257:.3f}s' in cross),
    ("startup removed from unattributed", '- n11_browser_startup_v236257' in cross),
    ("ledger preserved", 'V23.62.55 N11 QUERY LEDGER' in cross),
    ("query timing preserved", 'V23.62.55 N11 QUERY TIMING' in cross),
    ("4500 preserved", 'strong-first gets a consolidated 4.5s navigation budget' in cross),
    ("350 recovery preserved", 'timeout=350' in cross),
    ("scope hotfix preserved", 'n11_timeout_selector_recovered_v236230 = False' in cross),
    ("v2350 recovery preserved", 'V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
    ("v2353 wiring preserved", 'V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
    ("security bypass disabled", '"security_challenge_bypass": "disabled"' in main),
    ("price integrity preserved", '"price_integrity_quarantine": "preserved"' in main),
    ("production unchanged", '"production_ingestion_behavior": "unchanged"' in main),
    ("bat no utf8 bom", not bat_bytes.startswith(b"\xef\xbb\xbf")),
]
failed=[]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ")+name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit("V23.62.57 smoke failed: "+", ".join(failed))
print(f"V23.62.57 smoke OK {len(checks)}/{len(checks)}")
