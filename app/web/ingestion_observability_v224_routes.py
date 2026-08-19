from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from app.services.ingestion_observability_v224_service import (
    get_product_history,
    get_recent_tasks,
    get_summary,
)
from app.services.ingestion_stress_v224_service import (
    get_stress_run,
    start_stress_run,
)

router = APIRouter(prefix="/api/ingestion-observability/v224", tags=["V22.4 Ingestion Observability"])


class StressRequest(BaseModel):
    urls: list[HttpUrl]


@router.get("/summary")
def summary():
    return get_summary()


@router.get("/tasks")
def tasks(limit: int = Query(50, ge=1, le=500)):
    return {
        "engine": "FIRSATAI_PRODUCTION_INGESTION_OBSERVABILITY",
        "engine_version": "22.4.0",
        "count": len(get_recent_tasks(limit)),
        "tasks": get_recent_tasks(limit),
    }


@router.get("/products/{global_product_id}")
def product_history(global_product_id: int, limit: int = Query(50, ge=1, le=500)):
    rows = get_product_history(global_product_id, limit)
    return {
        "engine_version": "22.4.0",
        "global_product_id": global_product_id,
        "ingestion_count": len(rows),
        "tasks": rows,
    }


@router.post("/stress/run")
def stress_run(
    payload: StressRequest,
    candidate_limit: int = Query(50, ge=5, le=100),
    parallel_workers: int = Query(3, ge=1, le=6),
    per_product_timeout_seconds: int = Query(300, ge=60, le=900),
):
    try:
        return start_stress_run(
            urls=[str(url) for url in payload.urls],
            candidate_limit=candidate_limit,
            parallel_workers=parallel_workers,
            per_product_timeout_seconds=per_product_timeout_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/stress/{run_id}")
def stress_status(run_id: str):
    row = get_stress_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Stress test görevi bulunamadı.")
    return row
