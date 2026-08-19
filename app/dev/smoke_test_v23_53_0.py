from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
rr=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.53.0"),
("hybrid order","V23.53 HYBRID PRIORITY ORDER" in c),
("rolling submit","def submit_next_v2353" in c),
("slot submit","V23.53 SLOT SUBMIT" in c),
("no strict wave loop",'for wave in (1, 2, 3):' not in c),
("queue serialization",'"queue_wait_seconds": row.queue_wait_seconds' in rr),
("execution serialization",'"execution_seconds": row.execution_seconds' in rr),
("wave serialization",'"scheduler_wave": row.scheduler_wave' in rr),
("aggregate queue","deep_refresh_total_queue_wait_seconds" in p),
("aggregate exec","deep_refresh_total_execution_seconds" in p),
("wave count","deep_refresh_wave_count" in p),
("n11 sequential preserved","N11 kalıcı Playwright profilini kullandığı için her zaman sıralı çalışır." in c),
("v2350 preserved","V23.50 HTTP-FIRST" in c),
("runtime","/api/runtime-identity/v2353" in m),
("v2352 runtime preserved","/api/runtime-identity/v2352" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
