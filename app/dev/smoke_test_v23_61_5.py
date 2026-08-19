from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))
from app.services.workload_priority_v23612 import (
    mark_user_deep_queued_v23612,
    mark_user_deep_done_v23612,
    user_deep_priority_active_v23612,
)

c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
rr=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")

mark_user_deep_queued_v23612("v23615-smoke")
active=user_deep_priority_active_v23612()
mark_user_deep_done_v23612("v23615-smoke")
cleared=not user_deep_priority_active_v23612()

scan_pos=c.index("def scan_other_stores")
lowest_gate_pos=c.index("V23.61.5 LOWEST-LAYER SCAN YIELD", scan_pos)
query_pos=c.index("search_query = self._build_search_query", scan_pos)

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.5"),
("priority active",active),
("priority cleared",cleared),
("cross workload param",'workload_class: str = "BACKGROUND"' in c),
("cross workload stored",'self.workload_class = str(workload_class or "BACKGROUND").upper()' in c),
("lowest gate","V23.61.5 LOWEST-LAYER SCAN YIELD" in c),
("lowest gate before query",scan_pos < lowest_gate_pos < query_pos),
("rolling slot gate","V23.61.5 ROLLING SLOT YIELD" in c),
("n11 lane gate","V23.61.5 N11 LANE YIELD" in c),
("repair propagates workload","workload_class=workload_class_v23614" in rr),
("production user workload",p.count('workload_class="USER_INGESTION"')>=2),
("runtime","/api/runtime-identity/v23615" in m),
("v23614 preserved","/api/runtime-identity/v23614" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
