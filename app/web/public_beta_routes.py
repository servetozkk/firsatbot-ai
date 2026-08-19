from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.services.public_beta_service import (
    ALLOWED_FEEDBACK_TYPES, ENGINE_VERSION, ensure_schema, list_feedback,
    public_beta_status, statistics, submit_feedback, update_feedback_status,
)

router = APIRouter(tags=["public-beta-v13"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

class FeedbackCreate(BaseModel):
    feedback_type: str
    message: str = Field(min_length=5, max_length=3000)
    page_path: str | None = Field(default=None, max_length=400)
    product_key: str | None = Field(default=None, max_length=180)
    store_code: str | None = Field(default=None, max_length=100)

class FeedbackStatusUpdate(BaseModel):
    status: Literal["new", "reviewing", "resolved", "rejected"]

@router.get("/api/public-beta/status")
def status_api():
    return public_beta_status(write_report=False)

@router.get("/api/public-beta/statistics")
def statistics_api(days: int = Query(30, ge=1, le=365)):
    return statistics(days)

@router.post("/api/public-beta/feedback", status_code=201)
def feedback_create(payload: FeedbackCreate):
    try:
        return submit_feedback(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/api/public-beta/feedback")
def feedback_list(status: str | None = None, limit: int = Query(100, ge=1, le=500)):
    try:
        return {"engine_version": ENGINE_VERSION, "items": list_feedback(status=status, limit=limit)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/api/public-beta/feedback/{feedback_id}/status")
def feedback_status(feedback_id: int, payload: FeedbackStatusUpdate):
    try:
        return update_feedback_status(feedback_id, payload.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/geri-bildirim", response_class=HTMLResponse)
def feedback_page(request: Request):
    return templates.TemplateResponse(request=request, name="public_beta_feedback.html", context={
        "page_title": "Geri Bildirim | FırsatAI Public Beta",
        "feedback_types": sorted(ALLOWED_FEEDBACK_TYPES),
        "engine_version": ENGINE_VERSION,
    })

@router.get("/admin/public-beta", response_class=HTMLResponse)
def public_beta_admin(request: Request):
    ensure_schema()
    report = public_beta_status(write_report=False)
    items = list_feedback(limit=100)
    return templates.TemplateResponse(request=request, name="public_beta_admin.html", context={
        "report": report, "feedback_items": items,
        "page_title": "Public Beta Yönetimi | FırsatAI",
        "engine_version": ENGINE_VERSION,
    })
