from pathlib import Path
r=Path(__file__).resolve().parents[2]
svc=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.46.0"),
("task id deep worker","def _background_deep_refresh(task_id: str" in svc),
("deep queued",'deep_refresh_status="QUEUED"' in svc),
("deep running",'deep_refresh_status="RUNNING"' in svc),
("deep completed",'deep_refresh_status="COMPLETED"' in svc),
("deep failed",'deep_refresh_status="FAILED"' in svc),
("task id submitted","str(task_id)" in svc and "_background_deep_refresh," in svc),
("post price audit","deep_refresh_price_integrity=audit" in svc),
("post reliability","deep_refresh_store_offer_reliability=offer_reliability" in svc),
("serving refreshed","served_best_price=serving.get" in svc and "served_store_count=int(serving.get" in svc),
("ready nonblocking",'stage="READY"' in svc and "_deep_executor.submit" in svc),
("runtime","/api/runtime-identity/v2346" in main),
("v2345 preserved","/api/runtime-identity/v2345" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
