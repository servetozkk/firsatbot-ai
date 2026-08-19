from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.database.database import SessionLocal
from app.database.models import GlobalProduct, ProductGroup
from app.services.wearable_identity_convergence_v225_service import (
    _canonical_global_source,
    _canonical_group_source,
    run_wearable_convergence,
)

router = APIRouter(
    prefix="/api/wearable-identity/v225",
    tags=["V22.5 Wearable Identity"],
)


@router.post("/audit")
def audit():
    try:
        return run_wearable_convergence()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.get("/status")
def status():
    db = SessionLocal()
    try:
        group_buckets = {}
        for row in db.query(ProductGroup).all():
            source = _canonical_group_source(row)
            if source:
                group_buckets.setdefault(source, []).append(int(row.id))

        global_buckets = {}
        for row in db.query(GlobalProduct).filter(GlobalProduct.status == "ACTIVE").all():
            source = _canonical_global_source(row)
            if source:
                global_buckets.setdefault(source, []).append(int(row.id))

        duplicate_groups = {
            source: ids for source, ids in group_buckets.items() if len(ids) > 1
        }
        duplicate_globals = {
            source: ids for source, ids in global_buckets.items() if len(ids) > 1
        }

        return {
            "engine": "FIRSATAI_WEARABLE_IDENTITY_CONVERGENCE",
            "engine_version": "22.5.0",
            "wearable_identity_bucket_count": len(group_buckets),
            "duplicate_wearable_product_group_bucket_count": len(duplicate_groups),
            "duplicate_wearable_global_product_bucket_count": len(duplicate_globals),
            "duplicate_product_groups": duplicate_groups,
            "duplicate_global_products": duplicate_globals,
            "converged": not duplicate_groups and not duplicate_globals,
        }
    finally:
        db.close()
