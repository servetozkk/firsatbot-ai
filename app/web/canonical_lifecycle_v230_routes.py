from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.canonical_lifecycle_v230_service import (
    install_database_guards,
    lifecycle_status,
)

router = APIRouter(
    prefix="/api/canonical-lifecycle/v230",
    tags=["V23.1 Canonical Lifecycle Contract"],
)


@router.get("/status")
def status(identity_source: str | None = Query(default=None)):
    return lifecycle_status(identity_source)


@router.post("/audit")
def audit():
    try:
        result = install_database_guards()
        result["status"] = lifecycle_status()
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
