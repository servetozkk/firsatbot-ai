from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.multi_store_offer_repair_v14_service import (
    get_multi_store_task,
    product_from_global_product,
    repair_product_across_stores,
)

router = APIRouter(tags=["Çok Mağazalı Teklif Birleştirme v14.9"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/admin/multi-store-repair", response_class=HTMLResponse)
def multi_store_repair_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_multi_store_repair_v14.html",
        context={},
    )


@router.post("/api/multi-store-repair/v14/products/{global_product_id}")
def repair_global_product(
    global_product_id: int,
    candidate_limit: int = Query(50, ge=10, le=50),
    parallel_workers: int = Query(3, ge=1, le=6),
):
    try:
        source = product_from_global_product(global_product_id)
        return repair_product_across_stores(
            source_product=source,
            target_global_product_id=global_product_id,
            candidate_limit=candidate_limit,
            parallel_workers=parallel_workers,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/api/multi-store-repair/v14/tasks/{task_id}")
def repair_task_status(task_id: str):
    task = get_multi_store_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    return task
