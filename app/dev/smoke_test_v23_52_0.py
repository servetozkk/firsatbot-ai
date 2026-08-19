from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.52.0"),
("wave helper","def _scheduler_wave_v2352" in c),
("wave jobs","wave_jobs:" in c),
("wave start","V23.52 WAVE" in c),
("queue wait field","queue_wait_seconds" in c),
("execution field","execution_seconds" in c),
("scheduler wave field","scheduler_wave" in c),
("telemetry queue","queue_wait_seconds" in p),
("telemetry execution","execution_seconds" in p),
("telemetry wave","scheduler_wave" in p),
("aggregate queue","deep_refresh_total_queue_wait_seconds" in p),
("aggregate exec","deep_refresh_total_execution_seconds" in p),
("wave count","deep_refresh_wave_count" in p),
("v2351 preserved","V23.51 ADAPTIVE STORE ORDER" in c),
("v2350 preserved","V23.50 HTTP-FIRST" in c),
("runtime","/api/runtime-identity/v2352" in m),
("v2351 runtime preserved","/api/runtime-identity/v2351" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
