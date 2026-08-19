from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from app.models.product import Product
from app.services.offer_matching_service import OfferMatchingService
from app.services.product_identity_service import ProductIdentityService

def p(name):
    return Product(name=name,price=1,old_price=None,rating=None,review_count=None,seller='',url='https://test.local/'+str(abs(hash(name))),image=None)
def ok(v,m):
    if not v: raise AssertionError(m)
    print('OK ',m)
def main():
    a=ProductIdentityService.parse(p('Samsung Galaxy A17 5G 8GB 256GB'))
    b=ProductIdentityService.parse(p('Samsung Galaxy A17 5G 8GB 512GB'))
    s,_=OfferMatchingService.score(a,b)
    ok(s==0,'farklı storage cross-store birleşmiyor')
    c=ProductIdentityService.parse(p('Lenovo V15 16GB RAM 512SSD'))
    d=ProductIdentityService.parse(p('Lenovo V15 16GB RAM 512 GB SSD'))
    s,_=OfferMatchingService.score(c,d)
    ok(s>=OfferMatchingService.MIN_MATCH_SCORE,'aynı laptop varyantı mağazalar arasında eşleşiyor')
    e=ProductIdentityService.parse(p('Samsung Galaxy A17 4G 8GB 256GB'))
    s,_=OfferMatchingService.score(a,e)
    ok(s==0,'4G ve 5G cross-store birleşmiyor')
    ok((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='11.2.0','VERSION 11.2.0')
    print('\nFırsatAI v11.2.0 smoke test başarılı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
