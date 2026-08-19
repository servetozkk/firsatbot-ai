from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))

from app.services.workload_priority_v23612 import (
    mark_user_deep_queued_v23612,
    mark_user_deep_done_v23612,
    user_deep_priority_active_v23612,
)

s=(r/"app/services/smart_catalog_refresh_v218_service.py").read_text(encoding="utf-8")
rr=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
c=(r/"app/scheduler.py").read_text(encoding="utf-8")
v=(r/"app/services/v9_catalog_ingestion_service.py").read_text(encoding="utf-8")
f=(r/"app/services/catalog_feed_v213_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")

mark_user_deep_queued_v23612("priority-smoke")
priority_active=user_deep_priority_active_v23612()
mark_user_deep_done_v23612("priority-smoke")
priority_cleared=not user_deep_priority_active_v23612()

smart_function_pos=s.index("def smart_refresh_product")
smart_gate_pos=s.index("V23.61.4 CENTRAL SMART REFRESH YIELD", smart_function_pos)
recover_pos=s.index("_recover_global_offers_from_legacy(product_id)", smart_function_pos)
repair_gate_pos=rr.index("V23.61.4 CENTRAL REPAIR YIELD")
active_repair_pos=rr.index("global _active_repair_count")

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.4"),
("priority helper active",priority_active),
("priority helper cleared",priority_cleared),
("smart workload param",'workload_class: str = "BACKGROUND"' in s),
("central smart gate","V23.61.4 CENTRAL SMART REFRESH YIELD" in s),
("smart gate before work",smart_gate_pos < recover_pos),
("repair workload param",'workload_class: str = "BACKGROUND"' in rr),
("central repair gate","V23.61.4 CENTRAL REPAIR YIELD" in rr),
("repair gate before active lock",repair_gate_pos < active_repair_pos),
("production explicit user",p.count('workload_class="USER_INGESTION"')>=2),
("legacy feed background",'workload_class="BACKGROUND"' in f),
("category gate","V23.61.4 CATEGORY SCHEDULER YIELD" in c),
("v9 gate","V23.61.4 V9 SCHEDULER YIELD" in v),
("runtime","/api/runtime-identity/v23614" in m),
("v23613 preserved","/api/runtime-identity/v23613" in m),
]
for n,val in checks:
    print(("OK  " if val else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
