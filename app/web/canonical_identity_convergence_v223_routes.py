from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.database.database import SessionLocal
from app.database.models import ProductGroup, GlobalProduct

from app.services.canonical_identity_convergence_v223_service import (
    canonical_phone_identity_source,
    run_identity_convergence,
)

router = APIRouter(
    prefix="/api/identity-convergence/v223",
    tags=["V22.3 Canonical Identity Convergence"],
)


@router.post("/audit")
def audit():
    try:
        return run_identity_convergence()
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
            source = canonical_phone_identity_source(row.identity_source, category=row.category)
            if source:
                group_buckets.setdefault(source, []).append(int(row.id))

        global_buckets = {}
        for row in db.query(GlobalProduct).filter(GlobalProduct.status == "ACTIVE").all():
            source = canonical_phone_identity_source(row.identity_source, category=row.category)
            if source:
                global_buckets.setdefault(source, []).append(int(row.id))

        duplicate_groups = {
            source: ids for source, ids in group_buckets.items() if len(ids) > 1
        }
        duplicate_globals = {
            source: ids for source, ids in global_buckets.items() if len(ids) > 1
        }
        return {
            "engine": "FIRSATAI_CANONICAL_IDENTITY_CONVERGENCE",
            "engine_version": "22.3.0",
            "phone_identity_bucket_count": len(group_buckets),
            "duplicate_phone_product_group_bucket_count": len(duplicate_groups),
            "duplicate_phone_global_product_bucket_count": len(duplicate_globals),
            "duplicate_product_groups": duplicate_groups,
            "duplicate_global_products": duplicate_globals,
            "converged": not duplicate_groups and not duplicate_globals,
        }
    finally:
        db.close()
