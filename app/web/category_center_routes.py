from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.services.category_center_service import category_detail, list_category_summaries, resolve_category
from app.services.breadcrumb_service import page_breadcrumbs

router = APIRouter(tags=["Kategori Merkezleri"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/kategoriler", response_class=HTMLResponse)
def category_index(request: Request):
    db = SessionLocal()
    try:
        categories = list_category_summaries(db)
        return templates.TemplateResponse(request=request, name="category_centers.html", context={"categories": categories, "page_title": "Kategori Merkezleri", "breadcrumbs_v13": page_breadcrumbs(("Kategoriler", None))})
    finally:
        db.close()

@router.get("/kategori/{category_slug}", response_class=HTMLResponse)
def category_page(request: Request, category_slug: str, sort: str = Query("price_asc")):
    db = SessionLocal()
    try:
        category = resolve_category(db, category_slug)
        if not category:
            raise HTTPException(status_code=404, detail="Kategori bulunamadı")
        data = category_detail(db, category, sort=sort)
        data["breadcrumbs_v13"] = page_breadcrumbs(("Kategoriler", "/kategoriler"), (category, None))
        return templates.TemplateResponse(request=request, name="category_center_detail.html", context=data)
    finally:
        db.close()

@router.get("/api/category-centers/v13")
def category_centers_api():
    db = SessionLocal()
    try:
        return {"engine_version": "13.4.2", "read_only": True, "categories": list_category_summaries(db)}
    finally:
        db.close()

@router.get("/api/category-centers/v13/{category_slug}")
def category_center_api(category_slug: str, sort: str = Query("price_asc")):
    db = SessionLocal()
    try:
        category = resolve_category(db, category_slug)
        if not category:
            raise HTTPException(status_code=404, detail="Kategori bulunamadı")
        return {"engine_version": "13.4.2", "read_only": True, **category_detail(db, category, sort=sort)}
    finally:
        db.close()
