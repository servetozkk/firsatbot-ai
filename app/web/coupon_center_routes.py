from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.services.coupon_center_service import ENGINE_VERSION, list_coupons

from app.services.breadcrumb_service import page_breadcrumbs
router = APIRouter(tags=["Kupon Sistemi v13.5.1"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/kuponlar", response_class=HTMLResponse)
def coupon_center(
    request: Request,
    store: str | None = None,
    category: str | None = None,
    type: str | None = None,
):
    db = SessionLocal()
    try:
        data = list_coupons(db, store=store, category=category, coupon_type=type)
        return templates.TemplateResponse(
            request=request,
            name="coupon_center.html",
            context={
                "coupons": data,
                "engine_version": ENGINE_VERSION,
                "seo_title": "Kupon Kodları ve Mağaza İndirimleri | FırsatAI",
                "seo_description": "Güncel mağaza kuponlarını, yüzde ve tutar indirimlerini ürün fiyatlarıyla birlikte karşılaştırın.",
                "canonical_url": str(request.base_url).rstrip("/") + "/kuponlar",
                "breadcrumbs": [("Ana Sayfa", "/"), ("Kuponlar", None)],
                "breadcrumbs_v13": page_breadcrumbs(("Kuponlar", None)),
            },
        )
    finally:
        db.close()


@router.get("/api/coupon-center/v13")
def coupon_api(
    store: str | None = None,
    category: str | None = None,
    type: str | None = None,
    limit: int = 100,
):
    db = SessionLocal()
    try:
        return list_coupons(
            db,
            store=store,
            category=category,
            coupon_type=type,
            limit=min(max(limit, 1), 250),
        )
    finally:
        db.close()
