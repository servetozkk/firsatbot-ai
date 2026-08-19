from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.catalog_feed_v213_service import (
    get_catalog_feed_status,
    run_catalog_feed_once,
)

router = APIRouter(prefix="/api/catalog-feed/v213", tags=["V21.3 Catalog Feed Engine"])


@router.get("/status")
def catalog_feed_status():
    return {
        "engine": "FIRSATAI_CATALOG_FEED_ENGINE",
        "engine_version": "21.3.0",
        **get_catalog_feed_status(),
    }


@router.post("/run")
def catalog_feed_run(
    limit: int = Query(default=3, ge=1, le=25),
    stale_hours: int = Query(default=6, ge=1, le=168),
    candidate_limit: int = Query(default=50, ge=5, le=100),
    parallel_workers: int = Query(default=3, ge=1, le=6),
):
    return run_catalog_feed_once(
        limit=limit,
        stale_hours=stale_hours,
        candidate_limit=candidate_limit,
        parallel_workers=parallel_workers,
    )


@router.post("/products/{global_product_id}/refresh")
def catalog_feed_refresh_product(
    global_product_id: int,
    candidate_limit: int = Query(default=50, ge=5, le=100),
    parallel_workers: int = Query(default=3, ge=1, le=6),
):
    return run_catalog_feed_once(
        limit=1,
        stale_hours=6,
        candidate_limit=candidate_limit,
        parallel_workers=parallel_workers,
        only_global_product_id=global_product_id,
    )
