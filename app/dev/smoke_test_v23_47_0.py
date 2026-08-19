from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8"); rr=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8"); p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8"); m=(r/"main.py").read_text(encoding="utf-8")
checks=[("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.47.1"),("duration field","duration_seconds: float | None = None" in c),("duration measure","perf_counter() - store_started_perf" in c),("duration serialized",'"duration_seconds": row.duration_seconds' in rr),("telemetry helper","_deep_refresh_store_telemetry_v2347" in p),("failure classifier","_classify_store_failure_v2347" in p),("failure breakdown","deep_refresh_failure_breakdown=failure_breakdown" in p),("slowest store","deep_refresh_slowest_store=max" in p),("lifecycle preserved",'deep_refresh_status="COMPLETED"' in p),("runtime","/api/runtime-identity/v2347" in m),("v2346 preserved","/api/runtime-identity/v2346" in m)]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
