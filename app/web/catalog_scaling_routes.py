from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.services.catalog_scaling_service import catalog_health, iter_products_ndjson, list_products_cursor

router = APIRouter(tags=["catalog-scaling-v13"])


@router.get("/api/products/v13")
def products_cursor_api(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(default=None),
):
    try:
        return list_products_cursor(cursor=cursor, limit=limit, category=category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/products/v13/stream")
def products_stream_api(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = Query(default=None),
):
    try:
        # Cursor erken doğrulanır; hata streaming başladıktan sonra oluşmaz.
        list_products_cursor(cursor=cursor, limit=1, category=category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        iter_products_ndjson(cursor=cursor, limit=limit, category=category),
        media_type="application/x-ndjson",
        headers={"X-FirsatAI-Pagination": "keyset"},
    )


@router.get("/api/catalog-health/v13")
def catalog_health_api():
    return catalog_health()
