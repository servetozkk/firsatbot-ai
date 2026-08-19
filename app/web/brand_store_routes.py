from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import ProductGroup, ProductOffer, Store

router = APIRouter(tags=["Marka ve Mağaza Sayfaları"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

STORE_LOGOS = {
    "trendyol": "/static/img/stores/trendyol.svg",
    "hepsiburada": "/static/img/stores/hepsiburada.svg",
    "amazon": "/static/img/stores/amazon.svg",
    "teknosa": "/static/img/stores/teknosa.svg",
    "mediamarkt": "/static/img/stores/mediamarkt.svg",
    "n11": "/static/img/stores/n11.svg",
    "ciceksepeti": "/static/img/stores/ciceksepeti.svg",
    "pazarama": "/static/img/stores/pazarama.svg",
}


def _logo_for(code: str | None, name: str | None) -> str:
    normalized = f"{code or ''} {name or ''}".casefold().replace("ç", "c").replace("ı", "i")
    for key, value in STORE_LOGOS.items():
        if key in normalized:
            return value
    return "/static/img/stores/generic.svg"


def _money(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _card(group, min_price, offer_count, best_store, old_price=None):
    price = _money(min_price)
    previous = _money(old_price)
    discount = 0
    if previous > price > 0:
        discount = max(0, min(99, round((previous - price) / previous * 100)))
    return {
        "id": group.id,
        "group_key": group.group_key,
        "name": group.canonical_name,
        "brand": group.brand or "Markasız",
        "category": group.category or "Diğer",
        "image": group.image,
        "price": price,
        "old_price": previous,
        "discount_percent": discount,
        "offer_count": int(offer_count or 0),
        "best_store": best_store or "Mağaza",
        "detail_url": f"/urun/{quote(str(group.group_key), safe='')}",
    }


def _group_cards(db, group_filter, store_id: int | None = None, limit: int = 60):
    query = (
        db.query(
            ProductGroup,
            func.min(ProductOffer.current_price).label("min_price"),
            func.count(ProductOffer.id).label("offer_count"),
            func.max(ProductOffer.old_price).label("old_price"),
        )
        .join(ProductOffer, ProductOffer.group_id == ProductGroup.id)
        .filter(group_filter)
    )
    if store_id is not None:
        query = query.filter(ProductOffer.store_id == store_id)
    rows = (
        query.group_by(ProductGroup.id)
        .order_by(func.min(ProductOffer.current_price).asc())
        .limit(limit)
        .all()
    )
    cards = []
    for group, min_price, offer_count, old_price in rows:
        best_offer_query = (
            db.query(ProductOffer, Store)
            .join(Store, Store.id == ProductOffer.store_id)
            .filter(ProductOffer.group_id == group.id)
        )
        if store_id is not None:
            best_offer_query = best_offer_query.filter(ProductOffer.store_id == store_id)
        best = best_offer_query.order_by(ProductOffer.current_price.asc()).first()
        best_store = best[1].name if best else "Mağaza"
        cards.append(_card(group, min_price, offer_count, best_store, old_price))
    return cards


@router.get("/marka/{brand_name}", response_class=HTMLResponse)
def brand_page(request: Request, brand_name: str):
    db = SessionLocal()
    try:
        clean = " ".join(brand_name.split()).strip()
        if not clean:
            raise HTTPException(status_code=404, detail="Marka bulunamadı")
        cards = _group_cards(db, ProductGroup.brand.ilike(clean))
        if not cards:
            cards = _group_cards(db, ProductGroup.brand.ilike(f"%{clean}%"))
        if not cards:
            raise HTTPException(status_code=404, detail="Marka bulunamadı")
        categories = {}
        for card in cards:
            categories[card["category"]] = categories.get(card["category"], 0) + 1
        prices = [card["price"] for card in cards if card["price"] > 0]
        return templates.TemplateResponse(
            request=request,
            name="brand_store_page.html",
            context={
                "page_type": "brand",
                "title": clean,
                "subtitle": f"{clean} ürünlerini, mağaza fiyatlarını ve güncel fırsatları karşılaştırın.",
                "logo_url": None,
                "cards": cards,
                "product_count": len(cards),
                "offer_count": sum(card["offer_count"] for card in cards),
                "lowest_price": min(prices) if prices else 0,
                "highest_price": max(prices) if prices else 0,
                "categories": sorted(categories.items(), key=lambda item: (-item[1], item[0]))[:8],
            },
        )
    finally:
        db.close()


@router.get("/magaza/{store_code}", response_class=HTMLResponse)
def store_page(request: Request, store_code: str):
    db = SessionLocal()
    try:
        store = (
            db.query(Store)
            .filter((Store.code.ilike(store_code)) | (Store.name.ilike(store_code)))
            .first()
        )
        if store is None:
            store = db.query(Store).filter(Store.name.ilike(f"%{store_code}%")).first()
        if store is None:
            raise HTTPException(status_code=404, detail="Mağaza bulunamadı")
        cards = _group_cards(db, ProductGroup.id.isnot(None), store_id=store.id)
        prices = [card["price"] for card in cards if card["price"] > 0]
        categories = {}
        for card in cards:
            categories[card["category"]] = categories.get(card["category"], 0) + 1
        return templates.TemplateResponse(
            request=request,
            name="brand_store_page.html",
            context={
                "page_type": "store",
                "title": store.name,
                "subtitle": f"{store.name} mağazasındaki ürünleri ve güncel fiyatları inceleyin.",
                "logo_url": _logo_for(store.code, store.name),
                "cards": cards,
                "product_count": len(cards),
                "offer_count": len(cards),
                "lowest_price": min(prices) if prices else 0,
                "highest_price": max(prices) if prices else 0,
                "categories": sorted(categories.items(), key=lambda item: (-item[1], item[0]))[:8],
            },
        )
    finally:
        db.close()
