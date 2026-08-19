from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.ai_comparison_v14_service import (
    analyze_global_product,
    data_quality_status,
)

router = APIRouter(tags=["AI Karşılaştırma ve Veri Kalitesi v14.5"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/admin/ai-comparison", response_class=HTMLResponse)
def ai_comparison_page(request: Request):
    status = data_quality_status()
    return templates.TemplateResponse(
        request=request,
        name="admin_ai_comparison_v14.html",
        context={"status": status},
    )


@router.get("/api/ai-comparison/v14/status")
def ai_comparison_status(limit: int = Query(500, ge=1, le=2000)):
    return data_quality_status(limit=limit)


@router.get("/api/ai-comparison/v14/products/{product_id}")
def ai_product_insight(product_id: int):
    result = analyze_global_product(product_id)
    if not result.get("available"):
        raise HTTPException(status_code=404, detail="Global ürün bulunamadı")
    return JSONResponse(result)
