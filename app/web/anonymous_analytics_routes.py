from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.services.anonymous_analytics_service import (
    ALLOWED_EVENT_TYPES,
    ENGINE_VERSION,
    dashboard,
    ensure_schema,
    product_metrics,
    record_event,
    search_metrics,
    store_metrics,
)

router = APIRouter(tags=["anonymous-analytics-v13"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


class AnalyticsEvent(BaseModel):
    event_type: str
    page_path: str | None = None
    search_query: str | None = None
    result_count: int | None = None
    product_key: str | None = None
    category: str | None = None
    brand: str | None = None
    store_code: str | None = None
    filter_name: str | None = None
    sort_name: str | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/api/analytics/v13/events", status_code=202)
def collect_event(payload: AnalyticsEvent):
    try:
        return record_event(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/analytics/v13")
def analytics_overview(days: int = Query(30, ge=1, le=365)):
    return dashboard(days)


@router.get("/api/analytics/v13/dashboard")
def analytics_dashboard_api(days: int = Query(30, ge=1, le=365)):
    return dashboard(days)


@router.get("/api/analytics/v13/searches")
def analytics_searches(days: int = Query(30, ge=1, le=365)):
    return search_metrics(days)


@router.get("/api/analytics/v13/products")
def analytics_products(days: int = Query(30, ge=1, le=365)):
    return product_metrics(days)


@router.get("/api/analytics/v13/stores")
def analytics_stores(days: int = Query(30, ge=1, le=365)):
    return store_metrics(days)


@router.get("/admin/analytics", response_class=HTMLResponse)
def analytics_admin(request: Request, days: int = Query(30, ge=1, le=365)):
    ensure_schema()
    return templates.TemplateResponse(
        request=request,
        name="anonymous_analytics_admin.html",
        context={
            "summary": dashboard(days),
            "selected_days": days,
            "event_types": sorted(ALLOWED_EVENT_TYPES),
            "page_title": "Kullanıcı Analitiği | FırsatAI",
            "engine_version": ENGINE_VERSION,
        },
    )
