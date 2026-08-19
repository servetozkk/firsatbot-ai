from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
o=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.29.0"),
("diagnostic collector","priceNodeDiagnostics" in h),
("same-card diagnostic selectors","diagnosticNodes" in h),
("diagnostic fields","parent_data_test_id" in h and "aria_label" in h),
("candidate diagnostic field","price_node_diagnostics" in h),
("cross diagnostic propagation","structured_node_diagnostics" in s),
("diagnostic summary log","V23.29 HB PRICE NODE DIAGNOSTIC SUMMARY" in s),
("diagnostic detail log","V23.29 HB PRICE NODE DIAGNOSTIC:" in s),
("trust unchanged","direct_offer_eligible" in s),
("pre-scrape preserved","V23.29 HB DIRECT PRE-SCRAPE GATE" in o),
("direct offer preserved","V23.29 HB SEARCH-CARD DIRECT VERIFIED OFFER" in o),
("runtime","/api/runtime-identity/v2329" in m),
("challenge bypass disabled",'security_challenge_bypass": "disabled"' in m),
("price integrity preserved","price_integrity_quarantine" in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
