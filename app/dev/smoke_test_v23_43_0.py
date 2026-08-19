from pathlib import Path
r=Path(__file__).resolve().parents[2]
matcher=(r/"app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")
repair=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.43.0"),
("motor markers","motoru" in matcher and "yedek motor" in matcher),
("case Turkish marker","kılıf" in matcher and "kilif" in matcher),
("filter markers","yedek filtre" in matcher and "hepa" in matcher),
("bare compatible omitted","compatible_accessory" not in matcher),
("matcher helper","def _generic_main_product_vs_accessory_guard_v2343" in matcher),
("generic strong model wired","role_ok_v2343" in matcher),
("final object wired","V23.43 FINAL OBJECT PRODUCT ROLE GATE" in repair),
("runtime","/api/runtime-identity/v2343" in main),
("v2342 preserved","/api/runtime-identity/v2342" in main),
("v2341 preserved","/api/runtime-identity/v2341" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
