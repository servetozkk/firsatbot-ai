from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.session import get_db
from app.services.stock_tracking_service import list_stock_items

router = APIRouter(tags=["stock-tracking-v13"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/stok", response_class=HTMLResponse)
def stock_center(
    request: Request,
    status: str | None = Query(default=None),
    store: str | None = Query(default=None),
    category: str | None = Query(default=None),
    db=Depends(get_db),
):
    data = list_stock_items(db, status=status, store=store, category=category)
    return templates.TemplateResponse(
        request=request,
        name="stock_center.html",
        context={"request": request, "stock_data": data},
    )


@router.get("/api/stock-center/v13")
def stock_center_api(
    status: str | None = Query(default=None),
    store: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=1000),
    db=Depends(get_db),
):
    return list_stock_items(db, status=status, store=store, category=category, limit=limit)
