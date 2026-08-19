from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))
from app.models.product import Product
from app.services.category_aware_matcher_v221 import (
    match_products_category_aware_v221,
    requires_raw_candidate_identity_v2333,
)

def mk(name,brand,category="Airfryer & Fritöz"):
    return Product(
        name=name,model=name,brand=brand,price=1500,old_price=None,
        rating=None,review_count=None,seller="test",url="https://x",
        image=None,category=category
    )

src=mk("Schafer Thermochef XL Airfryer Sıcak Hava Fritözü Siyah","Schafer")
good=mk("Schafer Thermochef XL Airfryer Sıcak Hava Fritözü Siyah","Schafer")
bad=mk("Schafer Fit Fry Dijital 3.5 L Siyah Airfryer Sıcak Hava Fritözü","Schafer")
g=match_products_category_aware_v221(source_product=src,candidate_product=good,minimum_score=0.82)
b=match_products_category_aware_v221(source_product=src,candidate_product=bad,minimum_score=0.82)

checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.33.0"),
("raw gate required",requires_raw_candidate_identity_v2333(src) is True),
("thermochef accepted",g[0] is True),
("fit fry rejected",b[0] is False),
("repair raw gate","V23.33 RAW CANDIDATE IDENTITY GATE" in (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")),
("evidence role runtime","ranking-selection-not-identity-injection" in (r/"main.py").read_text(encoding="utf-8")),
("v2332 preserved","/api/runtime-identity/v2332" in (r/"main.py").read_text(encoding="utf-8")),
("v2331 preserved","/api/runtime-identity/v2331" in (r/"main.py").read_text(encoding="utf-8")),
("v2330 preserved","/api/runtime-identity/v2330" in (r/"main.py").read_text(encoding="utf-8")),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
