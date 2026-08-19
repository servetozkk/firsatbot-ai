from pathlib import Path
r=Path(__file__).resolve().parents[2]
hb=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
reg=(r/"app/stores/adapters/registry.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
o=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.21.0"),
("HB adapter file","HEPSIBURADA_ADAPTER" in hb),
("HB registered","HEPSIBURADA_ADAPTER.code" in reg),
("same card selectors","product-card" in hb),
("current price priority","price-current-price" in hb),
("structured price marker","V23.21_STRUCTURED_CARD_PRICE" in hb),
("v2320 single price preserved","len(prices) != 1" in o),
("html fallback price disabled","html_fallback" in s),
("runtime","/api/runtime-identity/v2321" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
