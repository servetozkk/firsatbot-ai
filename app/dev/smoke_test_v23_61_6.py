from pathlib import Path
import sys, subprocess, json
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))

from app.services.workload_priority_v23612 import (
    clear_all_priority_leases_v23616,
    mark_user_deep_queued_v23612,
    mark_user_deep_running_v23612,
    mark_user_deep_done_v23612,
    user_deep_priority_active_v23612,
    user_deep_priority_snapshot_v23612,
)

g=(r/"app/services/workload_priority_v23612.py").read_text(encoding="utf-8")
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")

clear_all_priority_leases_v23616()
mark_user_deep_queued_v23612("v23616-smoke")
snap=user_deep_priority_snapshot_v23612()
active=user_deep_priority_active_v23612()

# Cross-process proof: a fresh Python process must see the same SQLite lease.
code = """
import sys, json
sys.path.insert(0, r'%s')
from app.services.workload_priority_v23612 import user_deep_priority_snapshot_v23612
print(json.dumps(user_deep_priority_snapshot_v23612()))
""" % str(r).replace("\\","\\\\")
proc=subprocess.run([sys.executable,"-c",code],capture_output=True,text=True,check=True)
cross_proc=json.loads(proc.stdout.strip())

wait=mark_user_deep_running_v23612("v23616-smoke")
mark_user_deep_done_v23612("v23616-smoke")
cleared=not user_deep_priority_active_v23612()

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.6"),
("sqlite backend","sqlite-cross-process" in g),
("wal mode",'PRAGMA journal_mode=WAL' in g),
("fail safe yield","return True" in g),
("local active",active and snap["count"]==1),
("cross process active",cross_proc.get("active") is True and cross_proc.get("count")==1),
("queue wait",wait>=0),
("clear works",cleared),
("primary heartbeat","V23.61.6: cross-process lease heartbeat" in p),
("lowest gate preserved","V23.61.5 LOWEST-LAYER SCAN YIELD" in c),
("runtime","/api/runtime-identity/v23616" in m),
("priority endpoint","/api/runtime-workload-priority/v23616" in m),
("v23615 preserved","/api/runtime-identity/v23615" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
print("CROSS_PROCESS_SNAPSHOT:",cross_proc)
raise SystemExit(0 if all(v for _,v in checks) else 1)
