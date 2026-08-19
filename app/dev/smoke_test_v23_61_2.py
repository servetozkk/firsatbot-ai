from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))
from app.services.workload_priority_v23612 import (
    mark_user_deep_queued_v23612,
    mark_user_deep_running_v23612,
    mark_user_deep_done_v23612,
    user_deep_priority_active_v23612,
)
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
s=(r/"app/services/smart_catalog_refresh_v218_service.py").read_text(encoding="utf-8")
f=(r/"app/services/catalog_feed_v213_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
mark_user_deep_queued_v23612("smoke-task")
active_after_queue=user_deep_priority_active_v23612()
queue_wait=mark_user_deep_running_v23612("smoke-task")
mark_user_deep_done_v23612("smoke-task")
inactive_after_done=not user_deep_priority_active_v23612()
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.2"),
("priority active",active_after_queue),
("queue wait numeric",queue_wait>=0),
("priority cleared",inactive_after_done),
("production queued hook","mark_user_deep_queued_v23612" in p),
("queue telemetry","deep_refresh_queue_wait_seconds" in p and "deep_refresh_queue_reason" in p),
("batch yield","V23.61.2 BACKGROUND BATCH YIELD" in s),
("feed yield","V23.61.2 CATALOG FEED YIELD" in f),
("no unsafe preemption","deferred_product_ids" in s),
("runtime","/api/runtime-identity/v23612" in m),
("v23611 preserved","/api/runtime-identity/v23611" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
