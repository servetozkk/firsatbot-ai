from pathlib import Path
import py_compile
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,name):
    checks.append((bool(cond),name)); print(("OK   " if cond else "FAIL ")+name)
main=(ROOT/"main.py").read_text(encoding="utf-8")
repair=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
ok((ROOT/"VERSION").read_text(encoding="utf-8").strip()=="23.62.92","VERSION 23.62.92")
ok('_RUNTIME_VERSION_V236292 = "23.62.92"' in main,"single runtime v236292")
ok('/api/runtime-identity/v236292' in main,"runtime endpoint v236292")
ok('/api/runtime-soak-stability/v236292' in main,"soak endpoint v236292")
force_block=main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236290")')]
ok('"runtime_version": _RUNTIME_VERSION_V236292' in force_block,"force response v236292")
ok('def _v236292_n11_exact_color_variant_url' in repair,"N11 exact-color resolver")
ok('V23.62.92 N11 EXACT-COLOR VARIANT RESOLVED' in repair,"N11 resolver telemetry")
ok('V23.62.92 N11 VARIANT TITLE PREFLIGHT' in repair,"fresh variant-title preflight")
ok('detail_family == source_family' in repair and 'detail_variants == source_variants' in repair and 'detail_storage == source_storage' in repair,"family variant storage exact gate")
ok('detail_color == source_color' in repair,"exact color gate")
ok('candidate_url = resolved_candidate_url_v236292' in repair,"resolved URL enters normal scraper")
ok('V23.35 DETAIL COLOR GATE' in repair,"authoritative color gate preserved")
ok('V23.62.91 AMAZON VERIFIED PHONE SEARCH-CARD OFFER' in repair,"Amazon v91 preserved")
ok('security_challenge_bypass": "disabled"' in main,"security bypass disabled")
ok('price_integrity_quarantine": "preserved"' in main,"price integrity preserved")
ok("'/urun/'" in repair and 'urljoin' in repair,"N11 linked variant URL extraction")
for p in [ROOT/"main.py", ROOT/"app/services/multi_store_offer_repair_v14_service.py"]: py_compile.compile(str(p),doraise=True)
ok(True,"critical Python compile")
failed=[n for c,n in checks if not c]
print(f"V23.62.92 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
