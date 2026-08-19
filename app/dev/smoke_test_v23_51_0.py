from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.51.0"),
("base priority","V2351_STORE_BASE_PRIORITY" in c),
("category bonus","V2351_CATEGORY_BONUS" in c),
("low yield penalty","V2351_LOW_YIELD_PENALTY" in c),
("kind helper","def _scheduler_product_kind_v2351" in c),
("priority helper","def _scheduler_priority_v2351" in c),
("order helper","def _ordered_definitions_v2351" in c),
("adaptive order log","V23.51 ADAPTIVE STORE ORDER" in c),
("scan ordering","definitions = self._ordered_definitions_v2351(" in c),
("telemetry priority","scheduler_priority" in p),
("telemetry reason","scheduler_reason" in p),
("telemetry search path","search_path" in p),
("v2350 preserved","V23.50 HTTP-FIRST" in c),
("runtime","/api/runtime-identity/v2351" in m),
("v2350 runtime preserved","/api/runtime-identity/v2350" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
