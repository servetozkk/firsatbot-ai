from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from app.services.production_ingestion_v220_service import (
    get_ingestion_task,
    runtime_info,
    start_production_ingestion,
)

router = APIRouter(prefix="/api/product-ingestion/v220", tags=["V22 Production Ingestion"])


class ProductIngestionRequest(BaseModel):
    url: HttpUrl


@router.get("/runtime")
def runtime():
    return runtime_info()


@router.post("/products")
def ingest(
    payload: ProductIngestionRequest,
    candidate_limit: int = Query(50, ge=5, le=100),
    parallel_workers: int = Query(6, ge=1, le=6),
    fast_ingest: bool = Query(True),
):
    try:
        return start_production_ingestion(
            url=str(payload.url),
            candidate_limit=candidate_limit,
            parallel_workers=parallel_workers,
            fast_ingest=fast_ingest,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.get("/tasks/{task_id}")
def task(task_id: str):
    row = get_ingestion_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Ingestion görevi bulunamadı.")
    return row
