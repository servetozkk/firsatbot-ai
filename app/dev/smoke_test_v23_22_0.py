from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.22.0"),
("currency mandatory",'if (!/(?:TL|₺)/i.test(text)) continue;' in h),
("no fake TL",'text += \' TL\'' not in h),
("semantic reject roles","indirim|kazanç|kazanc|kupon|puan|taksit" in h),
("old price rejected","old|original|strike|cross|list-price|before-discount" in h),
("v2322 marker","V23.22_SEMANTIC_CURRENT_PRICE" in h),
("cross store marker","V23.22 HB semantik güncel fiyat" in s),
("v2321 adapter preserved","HEPSIBURADA_ADAPTER" in (r/"app/stores/adapters/registry.py").read_text(encoding="utf-8")),
("runtime","/api/runtime-identity/v2322" in m),
("price integrity preserved","price_integrity_quarantine" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
