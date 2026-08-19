from pathlib import Path
r=Path(__file__).resolve().parents[2]
matcher=(r/"app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
block=matcher[matcher.index("def _generic_accessory_role_v2343"):matcher.index("def _generic_main_product_vs_accessory_guard_v2343")]
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.45.0"),
("charging case",'"sarj kutusu"' in block and '"charging case"' in block),
("airfryer basket",'"airfryer sepeti"' in block and '"pisirme haznesi"' in block),
("air purifier filter",'"filtre seti"' in block and '"filter kit"' in block),
("mop hardened",'"mop seti"' in block),
("battery hardened",'"batarya paketi"' in block),
("carrying case",'"tasima cantasi"' in block),
("maintenance",'"kirec cozucu"' in block and '"descaler"' in block),
("spare set",'"tirnak seti"' in block),
("bag preserved",'"bez torba"' in block),
("motor preserved",'"motoru"' in block),
("bare compatible omitted",'"uyumlu"' not in block),
("runtime","/api/runtime-identity/v2345" in main),
("v2344 preserved","/api/runtime-identity/v2344" in main),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
