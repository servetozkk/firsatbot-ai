from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.scraper_operations_service import build_scraper_operations_report

router = APIRouter(tags=["Scraper Operations v14"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/api/scraper-operations/v14")
def scraper_operations_status():
    return build_scraper_operations_report()


@router.get("/admin/scraper-operations", response_class=HTMLResponse)
def scraper_operations_admin(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_scraper_operations_v14.html",
        context={
            "report": build_scraper_operations_report(),
        },
    )
