from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
main = (ROOT / "main.py").read_text(encoding="utf-8")
cross = (ROOT / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
repair = (ROOT / "app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
bat_bytes = (ROOT / "BASLAT_V23_62_58.bat").read_bytes()

m = re.search(r'@app\.get\("/api/runtime-identity/v236258"\)\ndef runtime_identity_v236258\(\):(?P<body>.*?)(?=\n\n@app\.get|\Z)', main, re.S)
identity_body = m.group("body") if m else ""

checks = [
    ("VERSION", version == "23.62.58"),
    ("runtime v236258", bool(m)),
    ("soak v236258", "/api/runtime-soak-stability/v236258" in main),
    ("single source v236258", '_RUNTIME_VERSION_V236258 = "23.62.58"' in main),
    ("force uses v236258", '"runtime_version": _RUNTIME_VERSION_V236258,\n            "test_only": True' in main),
    ("runtime identity uses v236258", '"runtime_version": _RUNTIME_VERSION_V236258' in identity_body),
    ("force response identity uses v236258", '"force_refresh_response_runtime_version": _RUNTIME_VERSION_V236258' in identity_body),
    ("no v236256 stale ref in v236258 identity", '_RUNTIME_VERSION_V236256' not in identity_body),
    ("runtime source v236258", 'single-source-v236258' in identity_body),
    ("browser startup telemetry preserved", 'V23.62.57 N11 BROWSER STARTUP' in cross),
    ("browser startup breakdown preserved", 'browser_startup={n11_browser_startup_v236257:.3f}s' in cross),
    ("ledger preserved", 'V23.62.55 N11 QUERY LEDGER' in cross),
    ("4500 preserved", 'strong-first gets a consolidated 4.5s navigation budget' in cross),
    ("350 recovery preserved", 'timeout=350' in cross),
    ("scope hotfix preserved", 'n11_timeout_selector_recovered_v236230 = False' in cross),
    ("v2350 recovery preserved", 'V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY' in repair),
    ("v2353 wiring preserved", 'V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING' in repair),
    ("security bypass disabled", '"security_challenge_bypass": "disabled"' in identity_body),
    ("price integrity preserved", '"price_integrity_quarantine": "preserved"' in identity_body),
    ("production unchanged", '"production_ingestion_behavior": "unchanged"' in identity_body),
    ("bat no utf8 bom", not bat_bytes.startswith(b"\xef\xbb\xbf")),
]
failed=[]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ")+name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit("V23.62.58 smoke failed: "+", ".join(failed))
print(f"V23.62.58 smoke OK {len(checks)}/{len(checks)}")
