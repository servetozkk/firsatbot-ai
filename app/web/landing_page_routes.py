from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.services.breadcrumb_service import page_breadcrumbs
from app.services.landing_page_service import ENGINE_VERSION, landing_detail, list_landings, resolve_landing

router = APIRouter(tags=["Landing Page Altyapısı v13.6.4"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/kesfet", response_class=HTMLResponse)
def landing_index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="landing_page_index.html",
        context={
            "items": list_landings(),
            "engine_version": ENGINE_VERSION,
            "seo_title": "Alışveriş Rehberleri ve Ürün Listeleri | FırsatAI",
            "seo_description": "Bütçe, kullanım amacı ve ürün özelliklerine göre hazırlanmış fiyat karşılaştırma sayfalarını keşfedin.",
            "canonical_url": str(request.base_url).rstrip("/") + "/kesfet",
            "breadcrumbs_v13": page_breadcrumbs(("Keşfet", None)),
        },
    )


@router.get("/kesfet/{slug}", response_class=HTMLResponse)
def landing_page(request: Request, slug: str):
    landing = resolve_landing(slug)
    if not landing:
        raise HTTPException(status_code=404, detail="Landing sayfası bulunamadı")
    db = SessionLocal()
    try:
        data = landing_detail(db, landing)
        return templates.TemplateResponse(
            request=request,
            name="landing_page_detail.html",
            context={
                **data,
                "engine_version": ENGINE_VERSION,
                "seo_title": landing.title,
                "seo_description": landing.description,
                "canonical_url": str(request.base_url).rstrip("/") + landing.url,
                "breadcrumbs_v13": page_breadcrumbs(("Keşfet", "/kesfet"), (landing.heading, None)),
            },
        )
    finally:
        db.close()


@router.get("/api/landing-pages/v13")
def landing_api():
    return {"engine_version": ENGINE_VERSION, "read_only": True, "items": list_landings()}


@router.get("/api/landing-pages/v13/{slug}")
def landing_detail_api(slug: str, limit: int = 72):
    landing = resolve_landing(slug)
    if not landing:
        raise HTTPException(status_code=404, detail="Landing sayfası bulunamadı")
    db = SessionLocal()
    try:
        return landing_detail(db, landing, limit=min(max(int(limit or 72), 1), 200))
    finally:
        db.close()
