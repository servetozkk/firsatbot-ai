from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))

from app.services.workload_priority_v23612 import (
    mark_user_deep_queued_v23612,
    mark_user_deep_running_v23612,
    mark_user_deep_done_v23612,
    user_deep_priority_active_v23612,
    user_deep_priority_snapshot_v23612,
)

p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
g=(r/"app/services/workload_priority_v23612.py").read_text(encoding="utf-8")
s=(r/"app/services/smart_catalog_refresh_v218_service.py").read_text(encoding="utf-8")
f=(r/"app/services/catalog_feed_v213_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")

# Functional idempotence.
mark_user_deep_queued_v23612("lease-smoke")
snap1=user_deep_priority_snapshot_v23612()
mark_user_deep_queued_v23612("lease-smoke")
snap2=user_deep_priority_snapshot_v23612()
wait=mark_user_deep_running_v23612("lease-smoke")
mark_user_deep_done_v23612("lease-smoke")

task_id_pos=p.index("task_id = uuid4().hex")
early_mark_pos=p.index("mark_user_deep_queued_v23612(str(task_id))", task_id_pos)
source_pos=p.index("source = ingest_source_product(url)", task_id_pos)

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.3"),
("lease before source",task_id_pos < early_mark_pos < source_pos),
("idempotent implementation",'row["state"]="QUEUED"' in g and '_user_deep_tasks.get(key)' in g),
("idempotent count",snap1["count"]==1 and snap2["count"]==1),
("queue wait measured",wait>=0),
("source failure cleanup","mark_user_deep_done_v23612(str(task_id))" in p),
("primary phase","PRIMARY_TIER_RUNNING" in p),
("deep queued phase","DEEP_REFRESH_QUEUED" in p),
("deep running phase","DEEP_REFRESH_RUNNING" in p),
("deep finished phase","DEEP_REFRESH_FINISHED" in p),
("batch yield preserved","V23.61.2 BACKGROUND BATCH YIELD" in s),
("feed yield preserved","V23.61.2 CATALOG FEED YIELD" in f),
("runtime","/api/runtime-identity/v23613" in m),
("v23612 preserved","/api/runtime-identity/v23612" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
