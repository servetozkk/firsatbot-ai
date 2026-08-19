from pathlib import Path
r=Path(__file__).resolve().parents[2]
matcher=(r/"app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.44.0"),
("bez torba marker",'"bez torba"' in matcher),
("supurge torbasi marker",'"supurge torbasi"' in matcher),
("toz torbasi marker",'"toz torbasi"' in matcher),
("dust bag marker",'"dust bag"' in matcher),
("motor guard preserved",'"motor"' in matcher and '"motoru"' in matcher),
("central guard preserved","def _generic_main_product_vs_accessory_guard_v2343" in matcher),
("runtime","/api/runtime-identity/v2344" in main),
("v2343 preserved","/api/runtime-identity/v2343" in main),
("v2342 preserved","/api/runtime-identity/v2342" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
