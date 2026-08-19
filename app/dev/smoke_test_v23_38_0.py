from pathlib import Path
r=Path(__file__).resolve().parents[2]
repair=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
product_service=(r/"app/services/product_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")

gate=repair.index("V23.38 TRUE FINAL OBJECT VARIANT GATE")
enrich=repair.index("candidate_product = ProductIdentityService.enrich_product(candidate_product)")
transfer=repair.index('"V23.7 kanonik kimlik aktarımı:"', gate)
save=repair.index("save_product(candidate_product)", gate)

checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.38.0"),
("save product enrich contract","product = ProductIdentityService.enrich_product(product)" in product_service),
("pre-enrich candidate",enrich<gate),
("final object snapshot","V23.38 FINAL OBJECT SNAPSHOT" in repair),
("final object gate","V23.38 TRUE FINAL OBJECT VARIANT GATE" in repair),
("hard reject","raise ValueError(reason_v2338)" in repair),
("gate before transfer",gate<transfer),
("gate before save",gate<save),
("same enriched object saved","save_product(candidate_product)" in repair[gate:save+60]),
("runtime","/api/runtime-identity/v2338" in main),
("v2337 preserved","/api/runtime-identity/v2337" in main),
("v2336 preserved","/api/runtime-identity/v2336" in main),
("v2330 preserved","/api/runtime-identity/v2330" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
