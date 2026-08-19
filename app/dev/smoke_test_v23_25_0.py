from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.25.0"),
("provenance records","structuredCandidates" in h and "priceProvenance" in h),
("generic data-price not intrinsically trusted","data-price', trustedRole.test(roleContext)" in h),
("trusted semantic JSON keys","currentPrice|salePrice|sellingPrice|finalPrice" in h),
("generic JSON price diagnostic","/^price$/i.test(key)" in h and "false" in h),
("accepted marker","V23.25_ACCEPTED_PRICE" in h),
("provenance marker","V23.25_STRUCTURED_PRICE_PROVENANCE" in h),
("HB marker-only extraction","accepted_match" in s and "definition.code == \"hepsiburada\"" in s),
("HB provenance debug","V23.25 HB PRICE ATTRIBUTE DEBUG" in s),
("runtime","/api/runtime-identity/v2325" in m),
("price integrity preserved","price_integrity_quarantine" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
