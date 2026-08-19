from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.services.price_comparison_core_v21_service import (
    get_product_price_comparison,
    search_global_catalog,
)


api_router = APIRouter(prefix="/api/price-comparison/v21", tags=["V21 Price Comparison Core"])
ui_router = APIRouter(prefix="/fiyat-karsilastirma", tags=["V21 Price Comparison UI"])
router = APIRouter()
router.include_router(api_router)
router.include_router(ui_router)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@api_router.get("/products/{global_product_id}")
def product_price_comparison(
    global_product_id: int,
    stale_hours: int = Query(default=6, ge=1, le=168),
):
    """Katalog-first ürün + mağaza teklif görünümü; canlı scrape başlatmaz."""
    db = SessionLocal()
    try:
        result = get_product_price_comparison(
            db=db,
            global_product_id=global_product_id,
            stale_hours=stale_hours,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Global ürün bulunamadı")
        return result
    finally:
        db.close()


@api_router.get("/search")
def catalog_search(
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=20, ge=1, le=50),
):
    """Kullanıcı aramasını mağazalara gitmeden global katalog üzerinden döndürür."""
    db = SessionLocal()
    try:
        items = search_global_catalog(db=db, query=q, limit=limit)
        return {
            "engine": "FIRSATAI_PRICE_COMPARISON_CORE",
            "engine_version": "21.3.0",
            "query": q,
            "count": len(items),
            "items": items,
            "live_scrape": False,
        }
    finally:
        db.close()


@ui_router.get("", response_class=HTMLResponse)
@ui_router.get("/", response_class=HTMLResponse)
def price_comparison_search_page(
    request: Request,
    q: str = Query(default="", max_length=160),
    limit: int = Query(default=20, ge=1, le=50),
):
    """Akakçe/Cimri tipi hızlı katalog arama sayfası. Canlı mağaza taraması yapmaz."""
    cleaned = " ".join((q or "").split()).strip()
    db = SessionLocal()
    try:
        items = search_global_catalog(db=db, query=cleaned, limit=limit) if len(cleaned) >= 2 else []
        return templates.TemplateResponse(
            request=request,
            name="price_comparison_search_v21.html",
            context={
                "query": cleaned,
                "items": items,
                "result_count": len(items),
                "seo_title": f"{cleaned} fiyat karşılaştırma | Fırsat AI" if cleaned else "Fiyat Karşılaştırma | Fırsat AI",
                "seo_description": "Fırsat AI global kataloğunda mağaza fiyatlarını hızlıca karşılaştırın.",
            },
        )
    finally:
        db.close()


@ui_router.get("/urun/{global_product_id}", response_class=HTMLResponse)
def price_comparison_product_page(
    request: Request,
    global_product_id: int,
    stale_hours: int = Query(default=6, ge=1, le=168),
):
    """Global ürünün hazır katalog tekliflerini kullanıcı dostu karşılaştırma sayfasında gösterir."""
    db = SessionLocal()
    try:
        result = get_product_price_comparison(
            db=db,
            global_product_id=global_product_id,
            stale_hours=stale_hours,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Global ürün bulunamadı")
        product = result["global_product"]
        return templates.TemplateResponse(
            request=request,
            name="price_comparison_product_v21.html",
            context={
                "comparison": result,
                "product": product,
                "summary": result["summary"],
                "offers": result["offers"],
                "best_offer": result["best_offer"],
                "seo_title": f"{product.get('name') or 'Ürün'} fiyatları | Fırsat AI",
                "seo_description": f"{product.get('name') or 'Ürün'} için mağaza fiyatlarını karşılaştırın ve en iyi teklifi görün.",
            },
        )
    finally:
        db.close()
