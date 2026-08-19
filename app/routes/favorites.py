from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.models import Favorite, ProductGroup
from app.services.user_identity_service import resolve_owner_key

router = APIRouter(prefix="/favorites", tags=["favorites"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def get_favorites(response: Response, visitor_id: str | None = Cookie(default=None), firsat_session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    key, user = resolve_owner_key(db, response, session_token=firsat_session, visitor_id=visitor_id)
    rows = db.query(Favorite).filter(Favorite.visitor_id == key).order_by(Favorite.created_at.desc()).all()
    return {"count": len(rows), "authenticated": user is not None, "favorites": [{"id": r.id, "product_group_id": r.product_group_id, "created_at": r.created_at.isoformat()} for r in rows]}


@router.post("/{group_id}")
def add_favorite(group_id: int, response: Response, visitor_id: str | None = Cookie(default=None), firsat_session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if db.query(ProductGroup.id).filter(ProductGroup.id == group_id).first() is None:
        raise HTTPException(404, "Ürün grubu bulunamadı.")
    key, user = resolve_owner_key(db, response, session_token=firsat_session, visitor_id=visitor_id)
    row = db.query(Favorite).filter(Favorite.visitor_id == key, Favorite.product_group_id == group_id).first()
    if row is None:
        row = Favorite(visitor_id=key, product_group_id=group_id)
        db.add(row); db.commit(); db.refresh(row)
    return {"success": True, "favorite_id": row.id, "authenticated": user is not None}


@router.delete("/{group_id}")
def remove_favorite(group_id: int, response: Response, visitor_id: str | None = Cookie(default=None), firsat_session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    key, user = resolve_owner_key(db, response, session_token=firsat_session, visitor_id=visitor_id)
    row = db.query(Favorite).filter(Favorite.visitor_id == key, Favorite.product_group_id == group_id).first()
    if row is not None:
        db.delete(row); db.commit()
    return {"success": True, "authenticated": user is not None}
