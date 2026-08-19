from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))
from app.models.product import Product
from app.services.category_aware_matcher_v221 import _audio_strong_family_v2332,_clean_brand_v2332,match_products_category_aware_v221
def mk(name,brand):
    return Product(
        name=name, model=name, brand=brand, price=1000, old_price=None,
        rating=None, review_count=None, seller="test", image=None,
        url="https://x", category="Kulaklık"
    )
src=mk("Huawei FreeBuds SE 2 Beyaz","Huawei")
white=mk("Huawei FreeBuds SE 2 Beyaz","Marka Huawei")
blue=mk("Huawei FreeBuds SE 2 Ada Mavisi","Huawei")
se3=mk("Huawei FreeBuds SE 3 Beyaz","Huawei")
ok=match_products_category_aware_v221(source_product=src,candidate_product=white,minimum_score=0.8)
bad_color=match_products_category_aware_v221(source_product=src,candidate_product=blue,minimum_score=0.8)
bad_gen=match_products_category_aware_v221(source_product=src,candidate_product=se3,minimum_score=0.8)
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.32.0"),
("brand clean",_clean_brand_v2332("Marka Schafer")=="schafer"),
("freebuds signature","freebuds se 2" in _audio_strong_family_v2332(src)),
("freebuds exact accepted",ok[0] is True and "V23.32" in ok[2]),
("color mismatch rejected",bad_color[0] is False and "renk farklı" in bad_color[2]),
("generation mismatch rejected",bad_gen[0] is False and "strong family" in bad_gen[2]),
("runtime","/api/runtime-identity/v2332" in (r/"main.py").read_text(encoding="utf-8")),
("v2331 preserved","/api/runtime-identity/v2331" in (r/"main.py").read_text(encoding="utf-8")),
("v2330 preserved","/api/runtime-identity/v2330" in (r/"main.py").read_text(encoding="utf-8")),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
