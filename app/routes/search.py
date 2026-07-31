from __future__ import annotations

from fastapi import (
    APIRouter,
    Query,
)

from app.database.database import SessionLocal
from app.services.search_service import (
    search_products,
)

router = APIRouter(
    prefix="/search",
    tags=["search"],
)


@router.get("")
def search(
    q: str = Query(..., min_length=1),
):
    db = SessionLocal()

    try:
        return search_products(
            db=db,
            query=q,
        )

    finally:
        db.close()
