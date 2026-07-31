from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.models import Favorite

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_visitor_id(
    visitor_id: str | None,
    response: Response,
) -> str:
    if visitor_id:
        return visitor_id

    new_id = str(uuid4())

    response.set_cookie(
        key="visitor_id",
        value=new_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
    )

    return new_id


@router.get("")
def list_favorites(
    response: Response,
    visitor_id: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    visitor = get_visitor_id(visitor_id, response)

    favorites = (
        db.query(Favorite)
        .filter(Favorite.visitor_id == visitor)
        .all()
    )

    return {
        "count": len(favorites),
        "favorites": [
            {
                "id": item.id,
                "product_group_id": item.product_group_id,
                "created_at": item.created_at,
            }
            for item in favorites
        ],
    }


@router.post("/{group_id}")
def add_favorite(
    group_id: int,
    response: Response,
    visitor_id: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    visitor = get_visitor_id(visitor_id, response)

    exists = (
        db.query(Favorite)
        .filter(
            Favorite.visitor_id == visitor,
            Favorite.product_group_id == group_id,
        )
        .first()
    )

    if exists:
        return {
            "success": True,
            "message": "Ürün zaten favorilerde.",
        }

    favorite = Favorite(
        visitor_id=visitor,
        product_group_id=group_id,
    )

    db.add(favorite)
    db.commit()
    db.refresh(favorite)

    return {
        "success": True,
        "favorite_id": favorite.id,
    }


@router.delete("/{group_id}")
def remove_favorite(
    group_id: int,
    response: Response,
    visitor_id: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    visitor = get_visitor_id(visitor_id, response)

    favorite = (
        db.query(Favorite)
        .filter(
            Favorite.visitor_id == visitor,
            Favorite.product_group_id == group_id,
        )
        .first()
    )

    if favorite is None:
        raise HTTPException(
            status_code=404,
            detail="Favori bulunamadı.",
        )

    db.delete(favorite)
    db.commit()

    return {
        "success": True,
    }
