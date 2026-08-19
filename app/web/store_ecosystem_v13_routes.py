from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.store_ecosystem_v13_8_0 import ecosystem_summary, onboarding_template

router = APIRouter(tags=["store-ecosystem-v13"])


@router.get("/api/store-ecosystem/v13")
def store_ecosystem_status() -> dict:
    return ecosystem_summary()


@router.get("/api/store-ecosystem/v13/onboarding-template")
def store_onboarding_template(
    code: str = Query(..., min_length=2, max_length=40),
    name: str = Query(..., min_length=2, max_length=100),
    domain: list[str] = Query(...),
) -> dict:
    try:
        return onboarding_template(code, name, domain)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
