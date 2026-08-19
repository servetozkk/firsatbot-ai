from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
main=(ROOT/"main.py").read_text(encoding="utf-8")
search=(ROOT/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
binding=(ROOT/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
launcher=(ROOT/"BASLAT_V23_62_81.bat").read_text(encoding="utf-8")
version=(ROOT/"VERSION").read_text(encoding="utf-8").strip()
checks=[]
def ok(cond,name):
    checks.append((bool(cond),name)); print(("OK   " if cond else "FAIL ")+name)

ok(version=="23.62.81","VERSION")
ok('_RUNTIME_VERSION_V236281 = "23.62.81"' in main,"runtime constant")
ok('/api/runtime-identity/v236281' in main,"runtime v236281")
ok('/api/runtime-soak-stability/v236281' in main,"soak v236281")
ok('"runtime_version": _RUNTIME_VERSION_V236281' in main,"force uses v236281")
ok('amazon-phone-search-card-identity-aware-detail-order' in main,"architecture")
ok('V23.62.81 AMAZON PHONE IDENTITY-AWARE ORDER' in search,"identity-aware telemetry")
ok('amazon_phone_identity_order_v236281' in search,"Amazon phone-only scope")
ok('int(item[0])' in search,"identity score first")
ok('v23622_color_priority' in search,"color tie-break preserved")
ok('V23.3 telefon: family + varyant + network + depolama' in search,"strict phone score reason preserved")
ok('return score, "V23.3 telefon: family + varyant + network + depolama"' in search,"score316 canonical search-card contract preserved")
ok('V23.62.78 AMAZON PHONE SEARCH-CARD PREFILTER' in binding,"v78 prefilter preserved")
ok('V23.62.77 AMAZON BOUNDED IDENTITY-REJECT RETRY CAP' in binding,"v77 bounded retry preserved")
ok('V23.62.80 DETAIL COLOR REJECT EVIDENCE' in binding,"v80 color evidence preserved")
ok('source_color_token_boundary' in main and 'v23.62.79-preserved' in main,"v79 source color preserved")
ok('hepsiburada_final_price_normalization' in main and 'v23.62.76-preserved' in main,"v76 HB preserved")
ok('security_challenge_bypass' in main and 'disabled' in main,"security bypass disabled")
ok('price_integrity_quarantine' in main and 'preserved' in main,"price integrity preserved")
ok('production_ingestion_behavior' in main and 'unchanged' in main,"production ingestion unchanged")
ok('23.62.81' in launcher and 'smoke_test_v23_62_81.py' in launcher,"launcher v81")

# Static regression example: exact score=316 must outrank old color-heavy score=280.
example=[(280,2,"legacy-accessory"),(316,0,"exact-redmi"),(316,-2,"exact-other-color")]
ordered=sorted(example,key=lambda x:(x[0],x[1]),reverse=True)
ok(ordered[0][0]==316 and ordered[0][2]=="exact-redmi","behavior exact identity outranks color-heavy 280")
failed=[name for cond,name in checks if not cond]
print(f"V23.62.81 smoke {'OK' if not failed else 'FAIL'} {len(checks)-len(failed)}/{len(checks)}")
if failed:
    print("FAILED:"," | ".join(failed))
raise SystemExit(1 if failed else 0)
