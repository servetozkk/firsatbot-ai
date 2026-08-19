from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from app.services.production_stress_v238_service import (
    get_stress_run,
    list_stress_runs,
    start_production_stress,
    stress_runtime_info,
)

router = APIRouter(
    prefix="/api/production-stress/v238",
    tags=["V23.8 Production Stress"],
)


class StressRequest(BaseModel):
    urls: list[HttpUrl]


@router.get("/runtime")
def runtime():
    return stress_runtime_info()


@router.post("/runs")
def create_run(
    payload: StressRequest,
    candidate_limit: int = Query(50, ge=5, le=100),
    parallel_workers: int = Query(3, ge=1, le=6),
    per_product_timeout_seconds: int = Query(300, ge=60, le=900),
):
    try:
        return start_production_stress(
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
    rows = list_stress_runs(limit)
    return {
        "engine": "FIRSATAI_PRODUCTION_STRESS_V238",
        "engine_version": "23.8.0",
        "count": len(rows),
        "runs": rows,
    }


@router.get("/runs/{stress_run_id}")
def run_status(stress_run_id: str):
    row = get_stress_run(stress_run_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Production stress görevi bulunamadı.",
        )
    return row
