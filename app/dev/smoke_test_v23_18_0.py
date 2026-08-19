from pathlib import Path
r=Path(__file__).resolve().parents[2]
t=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[("VERSION",(r/"VERSION").read_text().strip()=="23.18.0"),("fallback helper","_v2318_generic_safe_fallback_product" in t),("score gate","score < 300" in t),("generic scope","generic_markers" in t),("currency mandatory","TL|₺" in t),("single price fail closed","len(prices) != 1" in t),("runtime","/api/runtime-identity/v2318" in m),("v2317 preserved","v2317_early_ready" in m)]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
