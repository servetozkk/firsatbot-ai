from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.store_offer_reliability_v226_service import (
    audit_product_offer_reliability_by_id,
    status_by_id,
)

router = APIRouter(
    prefix="/api/store-offer-reliability/v226",
    tags=["V22.6 Store Offer Reliability"],
)


@router.get("/products/{global_product_id}")
def status(global_product_id: int):
    try:
        return status_by_id(global_product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/products/{global_product_id}/audit")
def audit(global_product_id: int):
    try:
        return audit_product_offer_reliability_by_id(global_product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
