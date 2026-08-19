from pathlib import Path
r=Path(__file__).resolve().parents[2]
main=(r/"main.py").read_text(encoding="utf-8")
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
hb=(r/"app/scrapers/hepsiburada.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.62.43"),
("runtime v236243","/api/runtime-identity/v236243" in main),
("single source","_RUNTIME_VERSION_V236243 = \"23.62.43\"" in main),
("force uses v236243",'"runtime_version": _RUNTIME_VERSION_V236243' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):]),
("strong first 4000",'(4_000 if n11_strong_first_budget_v236234 else 4_500)' in c),
("old strong 3750 removed",'(3_750 if n11_strong_first_budget_v236234 else 4_500)' not in c),
("v236243 marker","V23.62.43 N11 STRONG-FIRST HYSTERESIS DEADBAND" in c),
("weak 4500 preserved",'else 4_500' in c),
("n11 detail cap preserved",'n11_detail_http_timeout_seconds": 4.5' in main),
("hb one second preserved","enumerate((1_000,), start=1)" in hb),
("security bypass disabled",'security_challenge_bypass": "disabled' in main),
("itopya preserved","v23.62.38-preserved" in main),
("idefix preserved","v23.62.36-preserved" in main),
("pazarama preserved","v23.62.31-preserved" in main),
]
for name,ok in checks:
    assert ok,name
    print("OK ",name)
