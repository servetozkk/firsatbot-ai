from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
o=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.30.0"),
("final-price selector",'[data-test-id^="final-price"]' in h and 'class*="finalPrice"' in h),
("fraction reject","fraction" in h),
("currency required",'(?:TL|₺)' in h),
("single final price","values.length !== 1" in h),
("coupon context reject","rejectRole.test(roleContext)" in h),
("trusted final source","dom-hepsiburada-final-price" in h),
("v2330 marker","V23.30_FINAL_PRICE_DIRECT_TRUST" in h),
("classified log","V23.30 HB FINAL-PRICE CLASSIFIED" in s),
("pre-scrape gate","V23.30 HB DIRECT PRE-SCRAPE GATE" in o),
("direct offer","V23.30 HB SEARCH-CARD DIRECT VERIFIED OFFER" in o),
("runtime","/api/runtime-identity/v2330" in m),
("challenge bypass disabled",'security_challenge_bypass": "disabled"' in m),
("price integrity preserved","price_integrity_quarantine" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
