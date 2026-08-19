from pathlib import Path
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.50.0"),
("requests import","import requests" in c),
("http stores",'V2350_HTTP_FIRST_STORES = {"gaminggen", "itopya", "incehesap"}' in c),
("http timeout","V2350_HTTP_TIMEOUT_SECONDS = 8" in c),
("http helper","def _http_first_candidate_urls_v2350" in c),
("healthy fast fail","V23.50 HTTP-FIRST FAST-FAIL" in c),
("http hit","V23.50 HTTP-FIRST HIT" in c),
("browser fallback preserved","V23.49 STORE LATENCY BUDGET" in c),
("detail validation preserved","self._is_same_product(" in c),
("telemetry preserved","deep_refresh_store_telemetry_count" in p),
("runtime","/api/runtime-identity/v2350" in m),
("v2349 preserved","/api/runtime-identity/v2349" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
