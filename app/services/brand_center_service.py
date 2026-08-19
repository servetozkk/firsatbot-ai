from __future__ import annotations

from app.services.seo_url_service import product_url
import re, unicodedata
from urllib.parse import quote, urlencode
from sqlalchemy import func
from app.database.models import ProductGroup, ProductOffer, Store

def slugify(value:str)->str:
    text=unicodedata.normalize("NFKD",str(value or "")); text="".join(c for c in text if not unicodedata.combining(c)); text=text.casefold().replace("ı","i")
    return re.sub(r"[^a-z0-9]+","-",text).strip("-")

def brand_url(name:str)->str: return f"/marka-merkezi/{quote(slugify(name),safe='')}"
def _money(v):
    try:return float(v or 0)
    except:return 0.0

def resolve_brand(db,slug):
    for (name,) in db.query(ProductGroup.brand).filter(ProductGroup.brand.isnot(None),ProductGroup.brand!='').distinct().all():
        if slugify(name)==slugify(slug): return str(name).strip()
    return None

def list_brand_summaries(db):
    rows=(db.query(ProductGroup.brand,func.count(func.distinct(ProductGroup.id)),func.count(ProductOffer.id),func.count(func.distinct(ProductGroup.category)),func.count(func.distinct(ProductOffer.store_id)),func.min(ProductOffer.current_price),func.max(ProductOffer.current_price),func.max(ProductGroup.image))
      .join(ProductOffer,ProductOffer.group_id==ProductGroup.id).filter(ProductGroup.brand.isnot(None),ProductGroup.brand!='',ProductOffer.current_price>0)
      .group_by(ProductGroup.brand).order_by(func.count(func.distinct(ProductGroup.id)).desc(),ProductGroup.brand.asc()).all())
    return [dict(name=str(b),slug=slugify(b),url=brand_url(b),product_count=int(pc or 0),offer_count=int(oc or 0),category_count=int(cc or 0),store_count=int(sc or 0),lowest_price=_money(lo),highest_price=_money(hi),image=img) for b,pc,oc,cc,sc,lo,hi,img in rows]

def _series_name(brand,name,model):
    text=f"{model or ''} {name or ''}".strip(); low=text.casefold(); b=str(brand or '').casefold()
    if b and low.startswith(b): text=text[len(str(brand)):].strip(' -')
    parts=[p for p in re.split(r"\s+",text) if p]
    return ' '.join(parts[:2]) if parts else 'Diğer'

def brand_detail(db,brand,sort='price_asc',limit=80):
    rows=(db.query(ProductGroup,func.min(ProductOffer.current_price),func.max(ProductOffer.old_price),func.count(ProductOffer.id),func.count(func.distinct(ProductOffer.store_id)))
      .join(ProductOffer,ProductOffer.group_id==ProductGroup.id).filter(ProductGroup.brand==brand,ProductOffer.current_price>0).group_by(ProductGroup.id).all())
    cards=[]; categories={}; series={}
    for g,price,old,offers,stores in rows:
        p=_money(price); o=_money(old); drop=round((o-p)/o*100,2) if o>p>0 else 0
        cat=str(g.category or 'Diğer'); ser=_series_name(brand,g.canonical_name,g.model)
        categories[cat]=categories.get(cat,0)+1; series[ser]=series.get(ser,0)+1
        cards.append(dict(id=g.id,identity_key=g.group_key,name=g.canonical_name,category=cat,series=ser,image=g.image,price=p,old_price=o,price_drop_percent=drop,offer_count=int(offers or 0),store_count=int(stores or 0),detail_url=product_url(g.canonical_name, g.group_key)))
    if sort=='price_desc': cards.sort(key=lambda x:(-x['price'],x['name']))
    elif sort=='stores': cards.sort(key=lambda x:(-x['store_count'],x['price']))
    elif sort=='price_drop': cards.sort(key=lambda x:(-x['price_drop_percent'],x['price']))
    elif sort=='newest': cards.sort(key=lambda x:-int(x['id'] or 0))
    else: cards.sort(key=lambda x:(x['price']<=0,x['price'],x['name']))
    stores=(db.query(Store.name,func.count(ProductOffer.id)).join(ProductOffer,ProductOffer.store_id==Store.id).join(ProductGroup,ProductGroup.id==ProductOffer.group_id).filter(ProductGroup.brand==brand,ProductOffer.current_price>0).group_by(Store.id).order_by(func.count(ProductOffer.id).desc()).limit(10).all())
    prices=[x['price'] for x in cards if x['price']>0]
    return dict(brand=brand,slug=slugify(brand),cards=cards[:max(1,min(int(limit),200))],product_count=len(rows),offer_count=sum(x['offer_count'] for x in cards),store_count=len(stores),lowest_price=min(prices) if prices else 0,highest_price=max(prices) if prices else 0,categories=sorted(categories.items(),key=lambda x:(-x[1],x[0]))[:12],series=sorted(series.items(),key=lambda x:(-x[1],x[0]))[:12],stores=[(str(n),int(c or 0)) for n,c in stores],filter_url='/arama?'+urlencode({'brand':brand}),sort=sort,seo={'title':f'{brand} Fiyatları ve Modelleri | FırsatAI','description':f'{brand} ürünlerini, güncel mağaza fiyatlarını, serileri ve fiyat düşüşlerini karşılaştırın.','canonical':brand_url(brand)},breadcrumb=[('Ana Sayfa','/'),('Markalar','/markalar'),(brand,brand_url(brand))])
