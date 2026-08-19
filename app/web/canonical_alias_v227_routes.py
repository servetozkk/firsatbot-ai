from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.database.database import SessionLocal
from app.database.models import GlobalProduct, ProductGroup
from app.services.canonical_alias_reliability_v227_service import (
    audit_all_aliases,
)

router = APIRouter(
    prefix="/api/canonical-alias/v227",
    tags=["V22.7 Canonical Alias Reliability"],
)


@router.get("/status")
def status():
    db = SessionLocal()
    try:
        globals_by_source = {}
        for row in db.query(GlobalProduct).filter(GlobalProduct.status == "ACTIVE").all():
            source = str(row.identity_source or "").strip()
            if source:
                globals_by_source.setdefault(source, []).append(int(row.id))

        groups_by_source = {}
        for row in db.query(ProductGroup).all():
            source = str(row.identity_source or "").strip()
            if source:
                groups_by_source.setdefault(source, []).append(int(row.id))

        duplicate_globals = {
            source: ids for source, ids in globals_by_source.items() if len(ids) > 1
        }
        duplicate_groups = {
            source: ids for source, ids in groups_by_source.items() if len(ids) > 1
        }
        return {
            "engine": "FIRSATAI_CANONICAL_ALIAS_RELIABILITY",
            "engine_version": "22.9.0",
            "duplicate_active_global_identity_source_count": len(duplicate_globals),
            "duplicate_product_group_identity_source_count": len(duplicate_groups),
            "duplicate_global_products": duplicate_globals,
            "duplicate_product_groups": duplicate_groups,
            "converged": not duplicate_globals and not duplicate_groups,
        }
    finally:
        db.close()


@router.post("/audit")
def audit():
    try:
        return audit_all_aliases()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
