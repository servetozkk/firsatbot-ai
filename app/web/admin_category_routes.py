from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.category_scrapers.registry import CategoryScraperRegistry
from app.services.category_scan_manager import category_scan_manager
from app.services.category_service import (
    add_category,
    delete_category,
    get_categories,
    set_category_active,
)


router = APIRouter(prefix="/admin/categories", tags=["Admin Kategoriler"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("", response_class=HTMLResponse)
def categories_page(request: Request, message: str | None = None, error: str | None = None):
    categories = get_categories()
    registry = CategoryScraperRegistry()
    return templates.TemplateResponse(
        request=request,
        name="admin_categories.html",
        context={
            "categories": categories,
            "stores": registry.list_stores(),
            "history": category_scan_manager.get_history(10),
            "message": message,
            "error": error,
        },
    )


@router.post("/create")
def create_category_form(
    name: str = Form(...),
    url: str = Form(...),
    limit: int = Form(100),
    active: bool = Form(False),
):
    success, message, _ = add_category(name=name, url=url, limit=limit, active=active)
    target = "/admin/categories?message=" if success else "/admin/categories?error="
    from urllib.parse import quote
    return RedirectResponse(target + quote(message), status_code=303)


@router.post("/{category_id}/toggle")
def toggle_category(category_id: str, active: bool = Form(...)):
    success, message, _ = set_category_active(category_id=category_id, active=active)
    from urllib.parse import quote
    if not success:
        return RedirectResponse(
            "/admin/categories?error=" + quote(message),
            status_code=303,
        )
    return RedirectResponse(
        "/admin/categories?message=" + quote(message),
        status_code=303,
    )


@router.post("/{category_id}/delete")
def delete_category_form(category_id: str):
    success, message = delete_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return RedirectResponse("/admin/categories", status_code=303)


@router.post("/{category_id}/scan")
def start_category_scan(category_id: str):
    try:
        task = category_scan_manager.start_category(category_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse({"success": True, "task": task})


@router.post("/scan-all")
def start_all_category_scans():
    try:
        task = category_scan_manager.start_all()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse({"success": True, "task": task})


@router.get("/tasks/{task_id}")
def get_scan_task(task_id: str):
    task = category_scan_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarama görevi bulunamadı.")
    return {"success": True, "task": task}
