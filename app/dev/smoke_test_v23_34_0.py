from pathlib import Path
import sys
r=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(r))
from app.models.product import Product
from app.services.category_aware_matcher_v221 import match_products_category_aware_v221,_generic_explicit_color_v2334

def mk(name,brand):
    return Product(name=name,model=name,brand=brand,price=1000,old_price=None,rating=None,review_count=None,seller="test",image=None,url="https://x",category="Dik Süpürge")

kiwi_src=mk("Kiwi KVC-4108 Dikey Elektrikli Süpürge Gri","Kiwi")
kiwi_gri=mk("Kiwi KVC-4108 Dikey Elektrikli Süpürge Gri","Kiwi")
kiwi_red=mk("Kiwi KVC-4108 Dikey Elektrikli Süpürge Kırmızı","Kiwi")
kiwi_white=mk("Kiwi KVC-4108 Kablolu Dikey Süpürge Beyaz","Kiwi")
fantom_src=mk("Fantom Pratic-S P1200 Dikey Süpürge Antrasit","Fantom")
fantom_red=mk("Fantom Pratik-S P1200 Dikey Süpürge Kırmızı","Fantom")
kg=match_products_category_aware_v221(source_product=kiwi_src,candidate_product=kiwi_gri,minimum_score=0.82)
kr=match_products_category_aware_v221(source_product=kiwi_src,candidate_product=kiwi_red,minimum_score=0.82)
kw=match_products_category_aware_v221(source_product=kiwi_src,candidate_product=kiwi_white,minimum_score=0.82)
fr=match_products_category_aware_v221(source_product=fantom_src,candidate_product=fantom_red,minimum_score=0.82)

checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.34.0"),
("kiwi gri detect",_generic_explicit_color_v2334(kiwi_src)=="gri"),
("kiwi same color accepted",kg[0] is True),
("kiwi red rejected",kr[0] is False and "V23.34 generic color" in kr[2]),
("kiwi white rejected",kw[0] is False and "V23.34 generic color" in kw[2]),
("fantom red rejected",fr[0] is False and "V23.34 generic color" in fr[2]),
("runtime","/api/runtime-identity/v2334" in (r/"main.py").read_text(encoding="utf-8")),
("v2333 preserved","/api/runtime-identity/v2333" in (r/"main.py").read_text(encoding="utf-8")),
("v2332 preserved","/api/runtime-identity/v2332" in (r/"main.py").read_text(encoding="utf-8")),
("v2330 preserved","/api/runtime-identity/v2330" in (r/"main.py").read_text(encoding="utf-8")),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
