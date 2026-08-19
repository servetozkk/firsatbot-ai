from pathlib import Path
r=Path(__file__).resolve().parents[2]
s=(r/"app/services/smart_catalog_refresh_v218_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.1"),
("reliability import","store_retry_intelligence_v2360" in s),
("context only upper","RELIABILITY_CONTEXT_CHANGE_ONLY" in s),
("backoff telemetry","RELIABILITY_BACKOFF_ACTIVE" in s),
("retry context","retry_context_v23611" in s),
("success freshness","timedelta(minutes=30)" in s),
("retry seconds next check","timedelta(seconds=float(retry_after_v23611))" in s),
("upper skip count","deep_refresh_smart_backoff_skipped_store_count" in p),
("upper skip details","deep_refresh_smart_backoff_skip_details" in p),
("lower scheduler preserved","deep_refresh_scheduler_skipped_store_count" in p),
("runtime","/api/runtime-identity/v23611" in m),
("v2361 preserved","/api/runtime-identity/v2361" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
