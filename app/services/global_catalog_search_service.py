from __future__ import annotations

from app.services.seo_url_service import product_url
from collections import defaultdict
from typing import Any
from app.database.models import GlobalOffer, GlobalProduct, GlobalProductVariant
from app.services.catalog_search_service import calculate_relevance
from app.services.performance_cache_service import global_search_cache

STORE_NAMES={'turkcellpasaj':'Turkcell Pasaj','trendyol':'Trendyol','hepsiburada':'Hepsiburada','amazon':'Amazon Türkiye','n11':'N11','pazarama':'Pazarama','teknosa':'Teknosa','mediamarkt':'MediaMarkt','vatan':'Vatan Bilgisayar','idefix':'İdefix','pttavm':'PttAVM','beymen':'Beymen'}

def _available(o):
    if not o.is_active or o.is_hidden or str(o.lifecycle_status or 'ACTIVE')!='ACTIVE' or float(o.current_price or 0)<=0: return False
    t=str(o.availability or '').casefold(); return not any(w in t for w in ('stokta yok','tükendi','stok dışı','out of stock'))

def _build(db,query):
    products=db.query(GlobalProduct).filter(GlobalProduct.status=='ACTIVE').order_by(GlobalProduct.updated_at.desc()).all()
    if not products: return []
    ids=[p.id for p in products]
    offers=db.query(GlobalOffer).filter(GlobalOffer.global_product_id.in_(ids),GlobalOffer.is_active.is_(True),GlobalOffer.is_hidden.is_(False),GlobalOffer.lifecycle_status=='ACTIVE',GlobalOffer.current_price>0).order_by(GlobalOffer.global_product_id,GlobalOffer.current_price).all()
    variants=db.query(GlobalProductVariant).filter(GlobalProductVariant.global_product_id.in_(ids)).all()
    om=defaultdict(list); vm=defaultdict(list)
    for x in offers: om[x.global_product_id].append(x)
    for x in variants: vm[x.global_product_id].append(x)
    out=[]
    for p in products:
        rows=om.get(p.id,[])
        if not rows: continue
        items=[]
        for o in rows:
            price=float(o.current_price or 0); shipping=float(o.shipping_price or 0); store=STORE_NAMES.get(o.store_code,str(o.store_code or '').title())
            items.append({'store':store,'store_code':o.store_code,'price':price,'old_price':float(o.old_price or 0),'shipping_price':shipping,'total_price':price+shipping,'availability':str(o.availability or ''),'global_variant_id':o.global_variant_id})
        items.sort(key=lambda i:(i['total_price'],i['store'])); best=items[0]; pv=vm.get(p.id,[])
        score=calculate_relevance(query,name=p.canonical_name,brand=p.normalized_brand,model=p.model or p.family,category=p.category,identity_source=str(p.identity_source or ''))
        if query and score<=0: continue
        colors=sorted({str(v.color).strip() for v in pv if str(v.color or '').strip()}); networks=sorted({str(v.network).strip() for v in pv if str(v.network or '').strip()})
        attrs={}
        if colors: attrs['color']=colors[0] if len(colors)==1 else 'Çok renk'
        if networks: attrs['network']=networks[0] if len(networks)==1 else 'Çoklu'
        stores=sorted({i['store'] for i in items if i['store']})
        out.append({'id':p.id,'name':p.canonical_name,'brand':str(p.normalized_brand or '').strip(),'model':str(p.model or p.family or '').strip(),'category':str(p.category or '').strip(),'image':p.primary_image,'price':best['total_price'],'product_price':best['price'],'shipping_price':best['shipping_price'],'offer_count':len(stores),'best_store':best['store'],'url':product_url(p.canonical_name, p.identity_key),'updated_at':p.updated_at,'relevance':score,'storage':f'{p.storage_gb}gb' if p.storage_gb is not None else '','ram':f'{p.ram_gb}gb' if p.ram_gb is not None else '','stores':stores,'in_stock':any(_available(o) for o in rows),'free_shipping':any(float(o.shipping_price or 0)<=0 for o in rows if _available(o)),'attributes':attrs,'offers':items,'global_product_id':p.id,'identity_key':p.identity_key,'variant_count':len(pv),'data_source':'global_catalog_v9','raw_product_count':int(p.raw_product_count or 0)})
    return out

def build_global_search_candidates(*,db,query:str)->list[dict[str,Any]]:
    q=' '.join(str(query or '').casefold().split())
    return global_search_cache.get_or_create(f'global-search:{q}',lambda:_build(db,query),90 if q else 45)
