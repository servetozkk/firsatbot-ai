from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.24.0"),
("structured selectors",'[data-current-price]' in h and 'itemprop="price"' in h),
("attribute names","data-selling-price" in h and "data-final-price" in h),
("same-card state","card?.attributes" in h),
("exactly one structured","structuredValues.length === 1" in h),
("v2324 marker","V23.24_STRUCTURED_PRICE_ATTRIBUTE" in h),
("cross marker","V23.24 HB structured attribute fiyatı" in s),
("runtime","/api/runtime-identity/v2324" in m),
("price integrity preserved","price_integrity_quarantine" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks:
    print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
