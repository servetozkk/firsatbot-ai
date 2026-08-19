from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))

from app.models.product import Product
from app.services.category_aware_matcher_v221 import _generic_explicit_color_v2334

def mk(name, brand="Kiwi"):
    return Product(
        name=name, model=name, brand=brand, price=1000, old_price=None,
        rating=None, review_count=None, seller="test", image=None,
        url="https://x", category="Dik Süpürge"
    )

src=mk("Kiwi KVC-4108 Dikey Elektrikli Süpürge Gri")
black=mk("KIWI KVC-4108 Şarjlı Dikey Süpürge Siyah")
grey=mk("KIWI KVC-4108 Dikey Süpürge Gri")

repair=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")

gate_marker='V23.35 DETAIL COLOR GATE'
gate_pos=repair.index(gate_marker)
local_window=repair[gate_pos-900:gate_pos+1200]

checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.35.0"),
("source gri",_generic_explicit_color_v2334(src)=="gri"),
("detail siyah",_generic_explicit_color_v2334(black)=="siyah"),
("detail gri",_generic_explicit_color_v2334(grey)=="gri"),
("gate marker",gate_marker in repair),
("gate uses raw candidate",'candidate_detail_color = _generic_explicit_color_v2334(candidate)' in local_window),
("gate fail closed",'continue' in local_window and 'rejection_reasons.append(reason)' in local_window),
("evidence follows gate",'evidence = getattr(self, "_candidate_evidence_by_url"' in repair[gate_pos:gate_pos+2200]),
("runtime","/api/runtime-identity/v2335" in main),
("v2334 preserved","/api/runtime-identity/v2334" in main),
("v2333 preserved","/api/runtime-identity/v2333" in main),
("v2330 preserved","/api/runtime-identity/v2330" in main),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
