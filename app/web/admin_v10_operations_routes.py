from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.services.operational_log_service import (
    clear_operation_events,
    operational_summary,
    read_operation_events,
)
from app.services.v10_release_service import build_release_diagnostics

router = APIRouter(prefix="/admin/v10-operations", tags=["V10 Operasyon Merkezi"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("", response_class=HTMLResponse)
def operations_page(
    request: Request,
    level: str | None = None,
    source: str | None = None,
    message: str | None = None,
):
    with SessionLocal() as db:
        release = build_release_diagnostics(db, require_live_scheduler=True)
    all_rows = read_operation_events(limit=2000, hours=168)
    events = read_operation_events(limit=400, level=level, source=source, hours=168)
    return templates.TemplateResponse(
        request=request,
        name="admin_v10_operations.html",
        context={
            "summary": operational_summary(),
            "events": events,
            "sources": sorted({str(row.get("source", "system")) for row in all_rows}),
            "selected_level": level or "",
            "selected_source": source or "",
            "release": release,
            "message": message,
        },
    )


@router.post("/clear-events")
def clear_events():
    count = clear_operation_events()
    return RedirectResponse(
        "/admin/v10-operations?message=" + quote(f"{count} operasyon olayı temizlendi."),
        status_code=303,
    )
