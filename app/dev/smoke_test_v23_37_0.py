from pathlib import Path
r=Path(__file__).resolve().parents[2]
repair=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
gate=repair.index("V23.37 PRE-CANONICAL VARIANT GATE")
transfer=repair.index('"V23.7 kanonik kimlik aktarımı:"', gate)
save=repair.index("save_product(candidate_product)", gate)
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.37.0"),
("central gate","V23.37 PRE-CANONICAL VARIANT GATE" in repair),
("hard reject","raise ValueError(reason_v2337)" in repair),
("gate before transfer",gate<transfer),
("gate before save",gate<save),
("final candidate authority","candidate_color_v2337 = _generic_explicit_color_v2334(candidate_product)" in repair),
("runtime","/api/runtime-identity/v2337" in main),
("v2336 preserved","/api/runtime-identity/v2336" in main),
("v2335 preserved","/api/runtime-identity/v2335" in main),
("v2333 preserved","/api/runtime-identity/v2333" in main),
("v2330 preserved","/api/runtime-identity/v2330" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
