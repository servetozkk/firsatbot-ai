from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.services.v10_release_service import (
    build_release_diagnostics,
    repair_release_integrity,
)

router = APIRouter(prefix='/admin/v10-release', tags=['V10 Release'])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / 'templates')
)


@router.get('', response_class=HTMLResponse)
def release_page(request: Request, message: str | None = None):
    with SessionLocal() as db:
        report = build_release_diagnostics(
            db,
            require_live_scheduler=True,
        )
    return templates.TemplateResponse(
        request=request,
        name='admin_v10_release.html',
        context={'report': report, 'message': message},
    )


@router.get('/report')
def release_report():
    with SessionLocal() as db:
        report = build_release_diagnostics(
            db,
            require_live_scheduler=True,
        )
    return JSONResponse(report)


@router.post('/repair')
def release_repair():
    with SessionLocal() as db:
        result = repair_release_integrity(db)
    message = 'Onarım tamamlandı: ' + ', '.join(
        f'{key}={value}' for key, value in result.items()
    )
    return RedirectResponse(
        f'/admin/v10-release?message={quote(message)}',
        status_code=303,
    )
