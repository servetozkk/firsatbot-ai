from types import SimpleNamespace

from app.models.product import Product
from app.services.offer_matching_service import OfferMatchingService
from app.services.product_identity_service import ProductIdentityService


def product(name: str, brand: str | None = None, model: str | None = None):
    return Product(name=name, price=1000, old_price=None, rating=None, review_count=None, seller='', url='https://example.com/' + name.replace(' ', '-'), image=None, brand=brand, model=model)


def group(group_id: int, source: str, name: str):
    return SimpleNamespace(
        id=group_id,
        identity_source=source,
        canonical_name=name,
        normalized_name=name.lower(),
        brand=source.split('brand=', 1)[1].split('|', 1)[0],
        model=None,
        category='Telefon',
    )


iphone_group = group(1, 'identity_v2:brand=apple|family=iphone 15|storage=128gb', 'Apple iPhone 15 128 GB Siyah')
s25_fe_group = group(2, 'identity_v2:brand=samsung|family=s25|variant=fe|ram=8gb|storage=256gb', 'Samsung Galaxy S25 FE 256 GB')

incoming = product('Apple iPhone 15 128GB Black', brand='Apple')
parsed = ProductIdentityService.parse(incoming)
score, reasons = OfferMatchingService.score(parsed, OfferMatchingService._group_identity(iphone_group))
assert score >= OfferMatchingService.MIN_MATCH_SCORE, (score, reasons)

wrong_capacity = product('Apple iPhone 15 256 GB Mavi', brand='Apple')
score2, reasons2 = OfferMatchingService.score(ProductIdentityService.parse(wrong_capacity), OfferMatchingService._group_identity(iphone_group))
assert score2 == 0 and 'depolama çelişiyor' in reasons2

base_s25 = product('Samsung Galaxy S25 256 GB 8 GB RAM', brand='Samsung')
score3, reasons3 = OfferMatchingService.score(ProductIdentityService.parse(base_s25), OfferMatchingService._group_identity(s25_fe_group))
assert score3 == 0 and 'model varyantı çelişiyor' in reasons3

class FakeQuery:
    def __init__(self, groups): self.groups = groups
    def filter(self, *_args, **_kwargs): return self
    def all(self): return self.groups
class FakeDB:
    def __init__(self, groups): self.groups = groups
    def query(self, _model): return FakeQuery(self.groups)

decision = OfferMatchingService.find_best_group(FakeDB([iphone_group, s25_fe_group]), incoming, [iphone_group, s25_fe_group])
assert decision.matched and decision.group.id == 1

print('OFFER MATCHING ENGINE V2 TESTLERİ BAŞARILI')
print('EŞLEŞME SKORU:', score)
print('EŞLEŞEN GRUP:', decision.group.id)
print('KAPASİTE ÇELİŞKİSİ: GÜVENLİ BİÇİMDE REDDEDİLDİ')
print('VARYANT ÇELİŞKİSİ: GÜVENLİ BİÇİMDE REDDEDİLDİ')
