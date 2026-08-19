from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))
from app.services.store_retry_scheduler_v2361 import (
    clear_retry_scheduler_state_v2361,
    record_store_attempt_v2361,
    scheduler_decision_v2361,
)
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
rr=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
clear_retry_scheduler_state_v2361()
ctx="huawei freebuds se 2"
initial=scheduler_decision_v2361(store_code="hepsiburada",context_key=ctx)
record_store_attempt_v2361(store_code="hepsiburada",context_key=ctx,success=False,failure_class="SECURITY_CHALLENGE")
security=scheduler_decision_v2361(store_code="hepsiburada",context_key=ctx)
record_store_attempt_v2361(store_code="n11",context_key=ctx,success=False,failure_class="IDENTITY_REJECT")
identity_same=scheduler_decision_v2361(store_code="n11",context_key=ctx)
identity_other=scheduler_decision_v2361(store_code="n11",context_key="different product")
record_store_attempt_v2361(store_code="trendyol",context_key=ctx,success=True,failure_class=None)
success=scheduler_decision_v2361(store_code="trendyol",context_key=ctx)
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.0"),
("initial allowed",initial["allow"] is True),
("security skipped",security["allow"] is False and security["retry_mode"]=="DEFERRED"),
("security remaining",int(security["retry_after_remaining_seconds"] or 0)>0),
("identity same blocked",identity_same["allow"] is False and identity_same["retry_mode"]=="CONTEXT_CHANGE_ONLY"),
("identity other allowed",identity_other["allow"] is True),
("success allowed",success["allow"] is True),
("cross hook","V23.61 RETRY SCHEDULER SKIP" in c),
("bridge skip",'"scheduler_skipped": row.scheduler_skipped' in rr),
("task skip count","deep_refresh_scheduler_skipped_store_count" in p),
("task snapshot","deep_refresh_retry_scheduler_state" in p),
("runtime","/api/runtime-identity/v2361" in m),
("v2360 runtime preserved","/api/runtime-identity/v2360" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
print("SECURITY:",security)
print("IDENTITY_SAME:",identity_same)
print("IDENTITY_OTHER:",identity_other)
raise SystemExit(0 if all(v for _,v in checks) else 1)
