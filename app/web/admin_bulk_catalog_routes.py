from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.bulk_catalog_manager import bulk_catalog_manager
from app.services.bulk_catalog_service import catalog_status, init_bulk_catalog_schema
from app.services.catalog_scan_plan_service import get_catalog_plans

router = APIRouter(tags=["Toplu Katalog v14.2"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/admin/bulk-catalog", response_class=HTMLResponse)
def bulk_catalog_page(request: Request):
    init_bulk_catalog_schema()
    return templates.TemplateResponse(
        request=request,
        name="admin_bulk_catalog.html",
        context={"plans": get_catalog_plans(), "status": catalog_status()},
    )


@router.post("/api/bulk-catalog/v14/plans/{plan_id}/run")
def start_bulk_plan(plan_id: str):
    return JSONResponse({"success": True, "task": bulk_catalog_manager.start(plan_id)})


@router.get("/api/bulk-catalog/v14/tasks/{task_id}")
def bulk_task(task_id: str):
    task = bulk_catalog_manager.get(task_id)
    if not task:
        raise HTTPException(404, "Toplu katalog görevi bulunamadı.")
    return {"success": True, "task": task}


@router.get("/api/bulk-catalog/v14/status")
def bulk_status():
    return catalog_status()
