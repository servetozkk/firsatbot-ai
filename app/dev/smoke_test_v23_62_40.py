from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(root/"main.py").read_text(encoding="utf-8")
v=(root/"VERSION").read_text(encoding="utf-8").strip()
checks=[
 ("VERSION",v=="23.62.40"),
 ("runtime v236240",'/api/runtime-identity/v236240' in m),
 ("force response metadata",'"runtime_version": "23.62.40"' in m),
 ("hysteresis marker",'V23.62.40 N11 STRONG-FIRST HYSTERESIS GUARD' in c),
 ("strong first 3750",'(3_750 if n11_strong_first_budget_v236234 else 4_500)' in c),
 ("weak 4500 preserved",'else 4_500' in c),
 ("detail soft cap preserved",'4.5' in m and 'n11_detail_http_timeout_seconds' in m),
 ("itopya preserved",'v23.62.38-preserved' in m),
 ("idefix preserved",'v23.62.36-preserved' in m),
 ("pazarama preserved",'v23.62.31-preserved' in m),
 ("trendyol preserved",'v23.62.29-preserved' in m),
 ("vatan preserved",'v23.62.27-preserved' in m),
 ("single flight preserved",'v23.62.25-preserved' in m),
 ("security bypass disabled",'"security_challenge_bypass": "disabled"' in m),
]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
if not all(ok for _,ok in checks): raise SystemExit(1)
