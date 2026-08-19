from __future__ import annotations

from app.services.seo_url_service import product_url

import re
from typing import Any
from sqlalchemy import case, distinct, func
from app.database.models import ProductGroup, ProductOffer, Store

ENGINE_VERSION = "13.5.0"


def _num(value: Any) -> float:
    try: return float(value or 0)
    except (TypeError, ValueError): return 0.0


def _classify(offer: ProductOffer) -> list[dict[str, str]]:
    tags: list[dict[str, str]] = []
    price, old = _num(offer.current_price), _num(offer.old_price)
    if old > price > 0:
        pct = round((old-price)/old*100)
        if pct >= 5: tags.append({"code":"price_drop","label":f"%{pct} fiyat düşüşü","kind":"discount"})
    if _num(offer.shipping_price) <= 0 or "ücretsiz" in (offer.shipping_method or "").casefold():
        tags.append({"code":"free_shipping","label":"Ücretsiz kargo","kind":"shipping"})
    text = " ".join(filter(None,[offer.campaign_text, offer.shipping_method, offer.delivery_text])).casefold()
    if any(x in text for x in ("taksit","peşin fiyatına","vade")):
        tags.append({"code":"installment","label":"Taksit avantajı","kind":"payment"})
    if any(x in text for x in ("sepette","indirim","kampanya","fırsat")):
        tags.append({"code":"store_campaign","label":(offer.campaign_text or "Mağaza kampanyası")[:90],"kind":"campaign"})
    if offer.is_official_seller:
        tags.append({"code":"official","label":"Resmî satıcı","kind":"trust"})
    return tags


def list_campaigns(db, campaign_type: str | None = None, store: str | None = None, category: str | None = None, limit: int = 200) -> dict[str, Any]:
    q=(db.query(ProductOffer, ProductGroup, Store)
       .join(ProductGroup, ProductGroup.id==ProductOffer.group_id)
       .join(Store, Store.id==ProductOffer.store_id)
       .filter(ProductOffer.is_active.is_(True), ProductOffer.current_price>0))
    if store: q=q.filter(func.lower(Store.code)==store.lower())
    if category: q=q.filter(func.lower(ProductGroup.category)==category.lower())
    rows=q.order_by(ProductOffer.checked_at.desc(), ProductOffer.current_price.asc()).limit(max(limit*4,400)).all()
    items=[]
    counts={"price_drop":0,"free_shipping":0,"installment":0,"store_campaign":0,"official":0}
    stores={}; categories={}
    for offer,group,st in rows:
        tags=_classify(offer)
        if campaign_type and not any(t["code"]==campaign_type for t in tags): continue
        if not tags: continue
        for t in tags: counts[t["code"]]=counts.get(t["code"],0)+1
        stores[st.code or st.name]=stores.get(st.code or st.name,0)+1
        cat=group.category or "Diğer"; categories[cat]=categories.get(cat,0)+1
        old=_num(offer.old_price); price=_num(offer.current_price)
        items.append({
            "offer_id":offer.id,"identity_key":group.group_key,"name":group.canonical_name,"brand":group.brand or "Markasız",
            "category":cat,"image":group.image,"store_code":st.code,"store_name":st.name,"price":price,"old_price":old,
            "discount_percent":round((old-price)/old*100,1) if old>price>0 else 0,"shipping_price":_num(offer.shipping_price),
            "delivery_text":offer.delivery_text,"campaign_text":offer.campaign_text,"tags":tags,"product_url":product_url(group.canonical_name, group.group_key),"store_url":offer.url,
        })
        if len(items)>=limit: break
    return {"engine_version":ENGINE_VERSION,"read_only":True,"items":items,"counts":counts,
            "stores":sorted(stores.items(),key=lambda x:(-x[1],x[0])),"categories":sorted(categories.items(),key=lambda x:(-x[1],x[0])),
            "filters":{"campaign_type":campaign_type,"store":store,"category":category}}
