from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.session import get_db
from app.services.new_products_service import list_new_products

router = APIRouter(tags=["new-products-v13"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/yeni-urunler", response_class=HTMLResponse)
def new_products_center(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    brand: str | None = Query(default=None),
    category: str | None = Query(default=None),
    store: str | None = Query(default=None),
    sort: str = Query(default="newest"),
    db=Depends(get_db),
):
    data = list_new_products(db, days=days, brand=brand, category=category, store=store, sort=sort)
    return templates.TemplateResponse(
        request=request,
        name="new_products_center.html",
        context={"request": request, "new_products_data": data},
    )


@router.get("/api/new-products/v13")
def new_products_api(
    days: int = Query(default=30, ge=1, le=365),
    brand: str | None = Query(default=None),
    category: str | None = Query(default=None),
    store: str | None = Query(default=None),
    sort: str = Query(default="newest"),
    limit: int = Query(default=200, ge=1, le=1000),
    db=Depends(get_db),
):
    return list_new_products(db, days=days, brand=brand, category=category, store=store, sort=sort, limit=limit)
