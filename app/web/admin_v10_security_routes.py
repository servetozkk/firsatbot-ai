from __future__ import annotations
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from app.middleware.security import clear_admin_cookie, issue_admin_cookie
from app.services.production_security_service import create_database_backup, production_security_report

router = APIRouter(tags=["V10 Security"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/admin/access", response_class=HTMLResponse)
def admin_access_page(request: Request, next: str = "/admin"):
    return templates.TemplateResponse(request=request, name="admin_access.html", context={"next_url": next, "error": None})

@router.post("/admin/access")
def admin_access_submit(request: Request, access_token: str = Form(...), next_url: str = Form("/admin")):
    if not settings.admin_access_token or access_token != settings.admin_access_token:
        return templates.TemplateResponse(request=request, name="admin_access.html", context={"next_url": next_url, "error": "Erişim anahtarı geçersiz."}, status_code=403)
    response = RedirectResponse(next_url if next_url.startswith("/admin") else "/admin", status_code=303)
    issue_admin_cookie(response); return response

@router.post("/admin/access/logout")
def admin_access_logout():
    response = RedirectResponse("/", status_code=303); clear_admin_cookie(response); return response

@router.get("/admin/v10-security", response_class=HTMLResponse)
def security_page(request: Request, message: str | None = None):
    return templates.TemplateResponse(request=request, name="admin_v10_security.html", context={"report": production_security_report(), "message": message})

@router.post("/admin/v10-security/backup")
def create_backup():
    result = create_database_backup()
    return RedirectResponse("/admin/v10-security?message=" + quote(f"Yedek doğrulandı: {result['path']}"), status_code=303)
