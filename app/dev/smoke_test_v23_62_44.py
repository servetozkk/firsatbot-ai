from pathlib import Path
r=Path(__file__).resolve().parents[2]
main=(r/"main.py").read_text(encoding="utf-8")
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
hb=(r/"app/scrapers/hepsiburada.py").read_text(encoding="utf-8")
force=main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):]
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.62.44"),
("runtime v236244","/api/runtime-identity/v236244" in main),
("single source",'_RUNTIME_VERSION_V236244 = "23.62.44"' in main),
("force uses v236244",'"runtime_version": _RUNTIME_VERSION_V236244' in force),
("hb search telemetry","V23.62.44 HB CHALLENGE PATH PHASE search" in c),
("hb candidate extraction telemetry","V23.62.44 HB CHALLENGE PATH PHASE candidate_extraction" in c),
("hb detail goto telemetry","V23.62.44 HB CHALLENGE PATH PHASE detail_goto" in hb),
("hb challenge detection telemetry","V23.62.44 HB CHALLENGE PATH PHASE challenge_detection" in hb),
("hb challenge recheck telemetry","V23.62.44 HB CHALLENGE PATH PHASE challenge_recheck" in hb),
("hb cleanup telemetry","V23.62.44 HB CHALLENGE PATH PHASE cleanup" in hb),
("hb total telemetry","V23.62.44 HB CHALLENGE PATH PHASE total" in hb),
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
