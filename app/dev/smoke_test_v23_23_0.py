from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.23.0"),
("leaf resolver","leafPriceNodes" in h),
("container parse disabled comment","container içeriği yerine yaprak" in h),
("currency mandatory",'if (!/(?:TL|₺)/i.test(text)) continue;' in h),
("single currency leaf","distinctCurrencyValues.length !== 1" in h),
("semantic reject roles","indirim|kazanç|kazanc|kupon|puan|taksit" in h),
("old price rejected","old|original|strike|cross|list-price|before-discount" in h),
("v2323 marker","V23.23_LEAF_CURRENT_PRICE" in h),
("cross store marker","V23.23 HB leaf güncel fiyat" in s),
("v2321 adapter preserved","HEPSIBURADA_ADAPTER" in (r/"app/stores/adapters/registry.py").read_text(encoding="utf-8")),
("runtime","/api/runtime-identity/v2323" in m),
("price integrity preserved","price_integrity_quarantine" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
