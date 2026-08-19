from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(c,n):
    checks.append((bool(c),n)); print(("OK  " if c else "FAIL"), n)
version=(ROOT/"VERSION").read_text(encoding="utf-8").strip()
main=(ROOT/"main.py").read_text(encoding="utf-8")
binding=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
hb=(ROOT/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
launcher=(ROOT/"BASLAT_V23_62_76.bat").read_text(encoding="utf-8")
ok(version=="23.62.76","VERSION")
ok('/api/runtime-identity/v236276' in main,"runtime v236276")
ok('/api/runtime-soak-stability/v236276' in main,"soak v236276")
ok('single-source-v236276' in main,"single source v236276")
ok('_RUNTIME_VERSION_V236276 = "23.62.76"' in main,"runtime constant")
ok('"runtime_version": _RUNTIME_VERSION_V236276' in main,"force/runtime uses v236276")
ok('V23.62.76: Turkish visible prices use a dot as thousands' in hb,"HB thousands parser marker")
ok("dotCount === 1" in hb and "normalized.split('.').pop().length === 3" in hb,"single-dot three-digit rule")
ok('V23.62.76 HB VERIFIED PHONE-WEARABLE SEARCH-CARD RECOVERY' in binding,"HB exact-card recovery marker")
ok('str(item.get("source") or "") == "dom-hepsiburada-final-price"' in binding,"trusted HB final-price provenance required")
ok('score >= 316' in binding,"score316 required")
ok('reason.startswith("V23.3 telefon:")' in binding,"exact phone scorer required")
ok('reason.startswith("V22.5 wearable:")' in binding,"exact wearable scorer required")
ok('V23.62.75 AMAZON BINDING REAL-PATH DETAIL CAP' in binding,"v75 Amazon cap preserved")
ok('v23.62.75-binding-force-path-first-detail-candidate-only' in main,"v75 Amazon metadata preserved")
ok('v23.62.69-jelatin-nano-cam-seramik-film-temperli-cam-hard-reject' in main,"phone accessory gate preserved")
ok('"security_challenge_bypass": "disabled"' in main,"security bypass disabled")
ok('"price_integrity_quarantine": "preserved"' in main,"price integrity preserved")
ok('smoke_test_v23_62_76.py' in launcher,"launcher calls v76 smoke")
ok('23.62.76' in launcher,"launcher version")
# Behavioral mirror for the exact locale normalization rule locked by source markers.
def norm(raw):
    cleaned=''.join(ch for ch in str(raw) if ch.isdigit() or ch in '.,')
    if ',' in cleaned:
        cleaned=cleaned.replace('.','').replace(',','.')
    else:
        dots=cleaned.count('.')
        if dots>1 or (dots==1 and len(cleaned.rsplit('.',1)[1])==3):
            cleaned=cleaned.replace('.','')
    return float(cleaned)
ok(norm('21.499 TL')==21499.0,"behavior 21.499 TL -> 21499")
ok(norm('1.848,70 TL')==1848.70,"behavior 1.848,70 TL -> 1848.70")
ok(norm('21.49 TL')==21.49,"behavior decimal-like 21.49 preserved")
failed=[n for c,n in checks if not c]
print(f"V23.62.76 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
