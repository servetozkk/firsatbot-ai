from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
rr=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.54.0"),
("dedicated n11 jobs","dedicated_n11_jobs" in c),
("dedicated executor",'thread_name_prefix="n11-dedicated-v2354"' in c),
("n11 concurrent start","V23.54 N11 DEDICATED LANE START" in c),
("old sequential tail removed","N11 sıralı taraması hata verdi" not in c),
("actual priority result","store_result.scheduler_priority = priority_v2353" in c),
("actual reason result","store_result.scheduler_reason = reason_v2353" in c),
("priority serialized",'"scheduler_priority": row.scheduler_priority' in rr),
("reason serialized",'"scheduler_reason": row.scheduler_reason' in rr),
("path serialized",'"search_path": row.search_path' in rr),
("production propagated",'row.get("scheduler_priority")' in p),
("rolling scheduler preserved","V23.53 HYBRID PRIORITY ORDER" in c),
("http first preserved","V23.50 HTTP-FIRST" in c),
("runtime","/api/runtime-identity/v2354" in m),
("v2353 runtime preserved","/api/runtime-identity/v2353" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
