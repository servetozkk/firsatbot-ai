from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.live_price_refresh_v14_service import (
    get_live_price_status,
    live_price_summary,
    start_live_price_refresh,
)

router = APIRouter(tags=["Canlı Fiyat Motoru v14.6"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("/admin/live-prices", response_class=HTMLResponse)
def live_prices_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_live_prices_v14.html",
        context={"summary": live_price_summary()},
    )


@router.get("/api/live-prices/v14/status")
def live_prices_status(task_id: str | None = None):
    return get_live_price_status(task_id=task_id)


@router.get("/api/live-prices/v14/summary")
def live_prices_summary():
    return live_price_summary()


@router.post("/api/live-prices/v14/refresh")
def live_prices_refresh(
    limit: int = Query(100, ge=1, le=2000),
    workers: int = Query(2, ge=1, le=4),
    retry_count: int = Query(2, ge=1, le=3),
    store_code: str | None = None,
):
    return start_live_price_refresh(
        limit=limit,
        workers=workers,
        retry_count=retry_count,
        store_code=store_code,
    )
