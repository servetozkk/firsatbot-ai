from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
m=(root/"main.py").read_text(encoding="utf-8")
c=(root/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
v=(root/"VERSION").read_text(encoding="utf-8").strip()
start=m.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")')
end=m.index("\n@app.", start+10)
force=m[start:end]
checks=[
 ("VERSION",v=="23.62.41"),
 ("runtime v236241",'/api/runtime-identity/v236241' in m),
 ("single source constant",'_RUNTIME_VERSION_V236241 = "23.62.41"' in m),
 ("force uses single source",'"runtime_version": _RUNTIME_VERSION_V236241' in force),
 ("force stale literal removed",'"runtime_version": "23.62.39"' not in force and '"runtime_version": "23.62.40"' not in force),
 ("runtime identity uses single source",'"force_refresh_response_runtime_version": _RUNTIME_VERSION_V236241' in m),
 ("hysteresis 3750 preserved",'(3_750 if n11_strong_first_budget_v236234 else 4_500)' in c),
 ("detail soft cap preserved",'n11_detail_http_timeout_seconds": 4.5' in m),
 ("itopya preserved",'v23.62.38-preserved' in m),
 ("idefix preserved",'v23.62.36-preserved' in m),
 ("pazarama preserved",'v23.62.31-preserved' in m),
 ("trendyol preserved",'v23.62.29-preserved' in m),
 ("vatan preserved",'v23.62.27-preserved' in m),
 ("single flight preserved",'v23.62.25-preserved' in m),
 ("security bypass disabled",'"security_challenge_bypass": "disabled"' in m),
]
for name,ok in checks:
 print(("OK  " if ok else "FAIL ")+name)
if not all(ok for _,ok in checks): raise SystemExit(1)
