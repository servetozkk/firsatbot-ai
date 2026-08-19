from pathlib import Path
r=Path(__file__).resolve().parents[2]
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
complete=p[p.index("def _complete_task"):p.index("def start_production_ingestion")]
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.10"),
("foreground read only helper","def _foreground_serving_snapshot_v236110" in p),
("background hard audit","def _background_final_integrity_audit_v236110" in p),
("no foreground mutating price audit","audit_product_prices(db=db" not in complete),
("no foreground mutating reliability audit","audit_product_offer_reliability(" not in complete),
("ready snapshot stage",'stage="READY_SNAPSHOT"' in complete),
("foreground policy","READ_ONLY_NO_SQLITE_WRITER" in complete),
("post ready audit queued",'post_ready_audit_status="QUEUED"' in complete),
("background invokes hard audit","_background_final_integrity_audit_v236110(" in p),
("runtime","/api/runtime-identity/v236110" in m),
("v23619 preserved","/api/runtime-identity/v23619" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
