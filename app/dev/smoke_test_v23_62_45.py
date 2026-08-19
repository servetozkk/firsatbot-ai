from pathlib import Path
r=Path(__file__).resolve().parents[2]
main=(r/"main.py").read_text(encoding="utf-8")
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
hb=(r/"app/scrapers/hepsiburada.py").read_text(encoding="utf-8")
force=main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):]
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.62.45"),
("runtime v236245","/api/runtime-identity/v236245" in main),
("single source",'_RUNTIME_VERSION_V236245 = "23.62.45"' in main),
("force uses v236245",'"runtime_version": _RUNTIME_VERSION_V236245' in force),
("hb selector marker","V23.62.45 HB SELECTOR FAST PATH" in c),
("hb productCard readiness","[class*=\"productCard\"]" in c),
("hb fast path included","or hb_selector_fast_path_v236245" in c),
("hb 150ms shared settle","150 if selector_fast_path_v236227 else settle_timeout" in c),
("hb phase telemetry preserved","V23.62.44 HB CHALLENGE PATH PHASE search" in c),
("hb one second preserved","enumerate((1_000,), start=1)" in hb),
("n11 strong 4000 preserved",'(4_000 if n11_strong_first_budget_v236234 else 4_500)' in c),
("n11 detail cap preserved",'"n11_detail_http_timeout_seconds": 4.5' in main),
("security bypass disabled",'"security_challenge_bypass": "disabled"' in main),
("itopya preserved","v23.62.38-preserved" in main),
("idefix preserved","v23.62.36-preserved" in main),
]
for name,ok in checks:
    assert ok,name
    print("OK ",name)
