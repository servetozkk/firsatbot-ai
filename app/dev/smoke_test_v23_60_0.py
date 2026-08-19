from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))
from app.services.store_retry_intelligence_v2360 import store_retry_intelligence_v2360, summarize_store_retry_intelligence_v2360

p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
security=store_retry_intelligence_v2360(success=False,failure_class="SECURITY_CHALLENGE")
identity=store_retry_intelligence_v2360(success=False,failure_class="IDENTITY_REJECT")
success=store_retry_intelligence_v2360(success=True,failure_class=None)
summary=summarize_store_retry_intelligence_v2360([
    {"store_code":"hb",**security},
    {"store_code":"amazon",**identity},
    {"store_code":"trendyol",**success},
])
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.60.0"),
("security deferred",security["retryable"] and security["retry_mode"]=="DEFERRED" and security["retry_after_seconds"]==1800),
("identity context only",(not identity["retryable"]) and identity["retry_mode"]=="CONTEXT_CHANGE_ONLY"),
("success 100",success["reliability_score"]==100 and success["retry_mode"]=="NONE"),
("summary retryable",summary["retryable_count"]==1 and summary["retryable_store_codes"]==["hb"]),
("telemetry reliability",'"reliability_score":retry_intel.get("reliability_score")' in p),
("telemetry retry mode",'"retry_mode":retry_intel.get("retry_mode")' in p),
("task retryable count","deep_refresh_retryable_store_count" in p),
("task average score","deep_refresh_average_reliability_score" in p),
("v2359 preserved","deep_refresh_bundle_prefilter_reject_count" in p),
("runtime","/api/runtime-identity/v2360" in m),
("v2359 runtime preserved","/api/runtime-identity/v2359" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
print("SECURITY_POLICY:",security)
print("IDENTITY_POLICY:",identity)
print("SUMMARY:",summary)
raise SystemExit(0 if all(v for _,v in checks) else 1)
