from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
)

from app.database.database import SessionLocal
from app.services.history_service import (
    get_product_price_history,
)


router = APIRouter(
    prefix="/price-history",
    tags=["price-history"],
)

@router.get("/{identity_key}")
def product_history(
    identity_key: str,
):
    db = SessionLocal()

    try:
        history = get_product_price_history(
            db=db,
            identity_key=identity_key,
        )

        if history is None:
            raise HTTPException(
                status_code=404,
                detail="Ürün grubu bulunamadı.",
            )

        return history

    finally:
        db.close()
