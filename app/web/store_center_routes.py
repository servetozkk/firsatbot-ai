from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database.database import SessionLocal
from app.services.store_center_service import ENGINE_VERSION, get_store_center, list_store_centers
from app.services.breadcrumb_service import page_breadcrumbs

router = APIRouter(tags=["Mağaza Merkezleri v13.4.4"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/magazalar", response_class=HTMLResponse)
def store_centers(request: Request):
    db = SessionLocal()
    try:
        stores = list_store_centers(db)
        return templates.TemplateResponse(request=request, name="store_centers.html", context={
            "stores": stores, "engine_version": ENGINE_VERSION, "seo_title": "Mağazalar ve Fiyat Teklifleri | FırsatAI",
            "seo_description": "Mağazaların ürün, teklif, kargo ve teslimat veri kapsamını karşılaştırın.",
            "canonical_url": str(request.base_url).rstrip("/") + "/magazalar",
            "breadcrumbs": [("Ana Sayfa", "/"), ("Mağazalar", None)], "breadcrumbs_v13": page_breadcrumbs(("Mağazalar", None)),
        })
    finally:
        db.close()

@router.get("/magaza-merkezi/{slug}", response_class=HTMLResponse)
def store_center_detail(request: Request, slug: str):
    db = SessionLocal()
    try:
        center = get_store_center(db, slug)
        if not center:
            raise HTTPException(status_code=404, detail="Mağaza bulunamadı")
        return templates.TemplateResponse(request=request, name="store_center_detail.html", context={
            "store": center, "seo_title": f"{center['name']} Fiyatları ve Teklifleri | FırsatAI",
            "seo_description": f"{center['name']} mağazasındaki ürünleri, fiyatları, kargo ve teslimat veri kapsamını inceleyin.",
            "canonical_url": str(request.base_url).rstrip("/") + f"/magaza-merkezi/{center['slug']}",
            "breadcrumbs": [("Ana Sayfa", "/"), ("Mağazalar", "/magazalar"), (center["name"], None)], "breadcrumbs_v13": page_breadcrumbs(("Mağazalar", "/magazalar"), (center["name"], None)),
        })
    finally:
        db.close()

@router.get("/api/store-centers/v13")
def store_centers_api():
    db = SessionLocal()
    try:
        return {"engine_version": ENGINE_VERSION, "read_only": True, "stores": list_store_centers(db)}
    finally:
        db.close()

@router.get("/api/store-centers/v13/{slug}")
def store_center_api(slug: str):
    db = SessionLocal()
    try:
        center = get_store_center(db, slug)
        if not center:
            raise HTTPException(status_code=404, detail="Mağaza bulunamadı")
        return center
    finally:
        db.close()
