from pathlib import Path
import sys, subprocess, json
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))

from app.services.workload_priority_v23612 import (
    clear_all_priority_leases_v23616,
    mark_user_deep_queued_v23612,
    mark_user_deep_done_v23612,
    user_priority_generation_v23617,
)

g=(r/"app/services/workload_priority_v23612.py").read_text(encoding="utf-8")
s=(r/"app/services/smart_catalog_refresh_v218_service.py").read_text(encoding="utf-8")
f=(r/"app/services/catalog_feed_v213_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")

clear_all_priority_leases_v23616()
g0=user_priority_generation_v23617()
mark_user_deep_queued_v23612("generation-smoke")
g1=user_priority_generation_v23617()
mark_user_deep_done_v23612("generation-smoke")
g2=user_priority_generation_v23617()

code = """
import sys, json
sys.path.insert(0, r'%s')
from app.services.workload_priority_v23612 import user_priority_generation_v23617
print(json.dumps({"generation": user_priority_generation_v23617()}))
""" % str(r).replace("\\","\\\\")
proc=subprocess.run([sys.executable,"-c",code],capture_output=True,text=True,check=True)
cross=json.loads(proc.stdout.strip())

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.7"),
("generation table","workload_priority_meta" in g),
("generation increments",g1==g0+1),
("generation persists after lease delete",g2==g1),
("cross process generation",cross.get("generation")==g2),
("batch generation capture","batch_generation_v23617" in s),
("pre product barrier","V23.61.7 BACKGROUND BATCH GENERATION YIELD" in s),
("post product barrier","V23.61.7 BACKGROUND BATCH POST-PRODUCT YIELD" in s),
("feed generation barrier","V23.61.7 CATALOG FEED GENERATION YIELD" in f),
("runtime","/api/runtime-identity/v23617" in m),
("generation endpoint","/api/runtime-priority-generation/v23617" in m),
("v23616 preserved","/api/runtime-identity/v23616" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
print("GEN:",g0,g1,g2,"CROSS:",cross)
raise SystemExit(0 if all(v for _,v in checks) else 1)
