from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.services.v11_stable_service import (
    build_stable_report,
    write_stable_report,
)


router = APIRouter(
    prefix="/admin/v11-stable",
    tags=["V11 Stable"],
)
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("", response_class=HTMLResponse)
def stable_page(request: Request, message: str | None = None):
    with SessionLocal() as db:
        report = build_stable_report(
            db,
            live_application=True,
        )
    return templates.TemplateResponse(
        request=request,
        name="admin_v11_stable.html",
        context={"report": report, "message": message},
    )


@router.get("/report")
def stable_report_json():
    with SessionLocal() as db:
        report = build_stable_report(
            db,
            live_application=True,
        )
    return JSONResponse(report)


@router.post("/validate")
def validate_stable():
    with SessionLocal() as db:
        report = build_stable_report(
            db,
            create_backup=True,
            repair=True,
            live_application=True,
        )
    path = write_stable_report(report)
    return RedirectResponse(
        "/admin/v11-stable?message="
        + quote(
            f"Doğrulama tamamlandı: {report['stable_status']} · {path}"
        ),
        status_code=303,
    )
