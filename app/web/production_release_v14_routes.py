from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.production_release_v14_service import ENGINE_VERSION, build_production_release

router = APIRouter(tags=["production-release-v14"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

@router.get("/api/production/v14")
def production_status(response: Response):
    report = build_production_release(write_report=False)
    if report["release_status"] != "PRODUCTION_RELEASE_READY":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report

@router.get("/admin/production-release", response_class=HTMLResponse)
def production_dashboard(request: Request):
    report = build_production_release(write_report=False)
    return templates.TemplateResponse(
        request=request,
        name="production_release_v14_admin.html",
        context={"report": report, "engine_version": ENGINE_VERSION, "page_title": "Production Release | FırsatAI"},
    )
