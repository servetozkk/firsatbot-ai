from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.49.0"),
("latency stores",'V2349_LATENCY_SENSITIVE_STORES = {"gaminggen", "itopya", "incehesap"}' in c),
("nav budget","V2349_NAVIGATION_TIMEOUT_MS = 15_000" in c),
("settle budget","V2349_SETTLE_TIMEOUT_MS = 700" in c),
("network budget","V2349_NETWORK_TIMEOUT_MS = 1_500" in c),
("query cap","V2349_MAX_QUERY_VARIANTS = 1" in c),
("query policy","definition.code in V2349_LATENCY_SENSITIVE_STORES" in c),
("budget marker","V23.49 STORE LATENCY BUDGET" in c),
("successful stores unchanged",'else:\n                    navigation_timeout = 25_000 if self.fast_mode else 60_000' in c),
("telemetry preserved","deep_refresh_store_telemetry_count" in p),
("runtime","/api/runtime-identity/v2349" in m),
("v2348 preserved","/api/runtime-identity/v2348" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
