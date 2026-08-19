from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(cond,name):
    checks.append((bool(cond),name)); print(("OK   " if cond else "FAIL ")+name)
main=(ROOT/"main.py").read_text(encoding="utf-8")
repair=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
ok((ROOT/"VERSION").read_text(encoding="utf-8").strip()=="23.62.91","VERSION 23.62.91")
ok('_RUNTIME_VERSION_V236291 = "23.62.91"' in main,"single runtime v236291")
ok('/api/runtime-identity/v236291' in main,"runtime endpoint v236291")
ok('/api/runtime-soak-stability/v236291' in main,"soak endpoint v236291")
force_block=main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236290")')]
ok('"runtime_version": _RUNTIME_VERSION_V236291' in force_block and '_RUNTIME_VERSION_V236290' not in force_block,"force response v236291")
ok('def _v236291_amazon_verified_phone_search_card_offer' in repair,"v91 Amazon verified phone helper")
ok('V23.62.91 AMAZON BRAND ALIAS VERIFIED' in repair,"narrow Xiaomi Redmi alias telemetry")
ok('brand == "xiaomi"' in repair and 'startswith("redmi note")' in repair,"Xiaomi to Redmi alias scope")
ok('V23.62.91 AMAZON VERIFIED PHONE SEARCH-CARD OFFER' in repair,"v91 verified card telemetry")
ok('if int(evidence.get("score") or 0) < 280' in repair,"score280 floor preserved")
ok('source_color_v236290 and detail_color_v236290' in repair,"explicit color gate preserved")
ok('attached_v236291 = force_attach_candidate_offer' in repair,"price-integrity attach preserved")
ok('security_challenge_bypass": "disabled"' in main,"security bypass disabled")
failed=[n for c,n in checks if not c]
print(f"V23.62.91 MASTER smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
raise SystemExit(1 if failed else 0)
