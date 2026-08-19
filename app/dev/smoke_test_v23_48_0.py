from pathlib import Path
r=Path(__file__).resolve().parents[2]
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.48.0"),
("success normalized",'"message":"OFFER_SAVED" if success else raw_message' in p),
("raw message preserved",'"raw_message":raw_message' in p),
("telemetry count","deep_refresh_store_telemetry_count=len(store_telemetry)" in p),
("success store codes","deep_refresh_success_store_codes=[" in p),
("failure store codes","deep_refresh_failure_store_codes=[" in p),
("failure breakdown preserved","deep_refresh_failure_breakdown=failure_breakdown" in p),
("slowest preserved","deep_refresh_slowest_store=max(store_telemetry" in p),
("lifecycle preserved",'deep_refresh_status="COMPLETED"' in p),
("runtime","/api/runtime-identity/v2348" in m),
("v23471 preserved","/api/runtime-identity/v23471" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
