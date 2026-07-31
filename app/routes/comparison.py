from __future__ import annotations

from fastapi import (
    APIRouter,
    HTTPException,
)

from app.database.database import SessionLocal
from app.services.comparison_service import (
    get_product_comparison,
)


router = APIRouter(
    prefix="/compare",
    tags=["compare"],
)


@router.get("/{identity_key}")
def compare_product(
    identity_key: str,
):
    """
    Merkezi ürün kimliğine bağlı mağaza tekliflerini
    karşılaştırmalı biçimde döndürür.
    """

    db = SessionLocal()

    try:
        comparison = get_product_comparison(
            db=db,
            identity_key=identity_key,
        )

        if comparison is None:
            raise HTTPException(
                status_code=404,
                detail="Ürün grubu bulunamadı.",
            )

        return comparison

    finally:
        db.close()
