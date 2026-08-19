from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.beta_readiness_service import ENGINE_VERSION, build_beta_readiness

router = APIRouter(tags=["beta-readiness-v13"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

@router.get("/api/system/health/v13")
def system_health():
    return build_beta_readiness(write_report=False)

@router.get("/api/beta-readiness/v13")
def beta_readiness():
    return build_beta_readiness(write_report=False)

@router.get("/admin/beta", response_class=HTMLResponse)
def beta_admin(request: Request):
    report = build_beta_readiness(write_report=False)
    return templates.TemplateResponse(request=request, name="beta_readiness_admin.html", context={"report": report, "page_title": "Kapalı Beta Hazırlığı | FırsatAI", "engine_version": ENGINE_VERSION})
