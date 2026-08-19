from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from app.services.bulk_ingestion_v232_service import (
    bulk_runtime_info,
    get_bulk_run,
    list_bulk_runs,
    start_bulk_ingestion,
)

router = APIRouter(
    prefix="/api/bulk-ingestion/v232",
    tags=["V23.2 Bulk Catalog Ingestion"],
)


class BulkIngestionRequest(BaseModel):
    urls: list[HttpUrl]


@router.get("/runtime")
def runtime():
    return bulk_runtime_info()


@router.post("/runs")
def create_run(
    payload: BulkIngestionRequest,
    candidate_limit: int = Query(50, ge=5, le=100),
    parallel_workers: int = Query(3, ge=1, le=6),
    per_product_timeout_seconds: int = Query(300, ge=60, le=900),
):
    try:
        return start_bulk_ingestion(
            urls=[str(url) for url in payload.urls],
            candidate_limit=candidate_limit,
            parallel_workers=parallel_workers,
            per_product_timeout_seconds=per_product_timeout_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.get("/runs")
def runs(limit: int = Query(20, ge=1, le=100)):
    rows = list_bulk_runs(limit)
    return {
        "engine": "FIRSATAI_BULK_CATALOG_INGESTION",
        "engine_version": "23.8.0",
        "count": len(rows),
        "runs": rows,
    }


@router.get("/runs/{run_id}")
def run_status(run_id: str):
    row = get_bulk_run(run_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Bulk ingestion görevi bulunamadı.",
        )
    return row
