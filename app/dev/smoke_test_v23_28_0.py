from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
o=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.28.0"),
("exact current selector state","matchedCurrentPriceSelector" in h),
("explicit currency resolver","explicitCurrencyPrice" in h),
("semantic current trusted source","dom-semantic-current-text" in h),
("ambiguous semantic source","dom-semantic-current-text-ambiguous" in h),
("generic price remains untrusted","data-price', trustedRole.test(roleContext)" in h),
("leaf exactly one","values.length === 1" in h),
("ambiguous diagnostic","values.length > 1" in h),
("v2328 marker","V23.28_DOM_PRICE_ROLE_CLASSIFICATION" in h),
("propagation preserved","V23.28 HB DOM PRICE ROLE CLASSIFIED" in s),
("pre-scrape gate","V23.28 HB DIRECT PRE-SCRAPE GATE" in o),
("direct offer","V23.28 HB SEARCH-CARD DIRECT VERIFIED OFFER" in o),
("runtime","/api/runtime-identity/v2328" in m),
("challenge bypass disabled",'security_challenge_bypass": "disabled"' in m),
("price integrity preserved","price_integrity_quarantine" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks:
    print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
