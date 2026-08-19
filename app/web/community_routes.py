from __future__ import annotations

from fastapi import APIRouter, Cookie, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.database.database import SessionLocal
from app.database.models import ProductGroup, ProductReview, ReviewVote
from app.web.account_routes import _current_user

router = APIRouter(prefix="/topluluk", tags=["community"])


def _redirect_to_group(group: ProductGroup, anchor: str = "topluluk") -> RedirectResponse:
    return RedirectResponse(url=f"/karsilastir/{group.group_key}#{anchor}", status_code=303)


@router.post("/yorum/{product_group_id}")
def create_review(
    product_group_id: int,
    request: Request,
    rating: int = Form(...),
    title: str = Form(""),
    body: str = Form(...),
    pros: str = Form(""),
    cons: str = Form(""),
    firsat_session: str | None = Cookie(default=None),
):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        group = db.query(ProductGroup).filter(ProductGroup.id == product_group_id).first()
        if group is None:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        if user is None:
            return RedirectResponse(url=f"/giris?next=/karsilastir/{group.group_key}%23topluluk", status_code=303)
        rating = max(1, min(5, int(rating)))
        clean_body = body.strip()
        if len(clean_body) < 10:
            return RedirectResponse(url=f"/karsilastir/{group.group_key}?review_error=Yorum en az 10 karakter olmalı#topluluk", status_code=303)
        review = (
            db.query(ProductReview)
            .filter(ProductReview.product_group_id == product_group_id, ProductReview.user_id == user.id)
            .first()
        )
        if review is None:
            review = ProductReview(product_group_id=product_group_id, user_id=user.id)
            db.add(review)
        review.rating = rating
        review.title = title.strip()[:160] or None
        review.body = clean_body[:4000]
        review.pros = pros.strip()[:1200] or None
        review.cons = cons.strip()[:1200] or None
        review.is_approved = True
        db.commit()
        return _redirect_to_group(group)
    finally:
        db.close()


@router.post("/yorum/{review_id}/faydali")
def toggle_helpful(review_id: int, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        review = db.query(ProductReview).filter(ProductReview.id == review_id).first()
        if review is None:
            raise HTTPException(status_code=404, detail="Yorum bulunamadı")
        group = db.query(ProductGroup).filter(ProductGroup.id == review.product_group_id).first()
        if user is None:
            return RedirectResponse(url=f"/giris?next=/karsilastir/{group.group_key}%23topluluk", status_code=303)
        vote = db.query(ReviewVote).filter(ReviewVote.review_id == review.id, ReviewVote.user_id == user.id).first()
        if vote:
            db.delete(vote)
        else:
            db.add(ReviewVote(review_id=review.id, user_id=user.id, is_helpful=True))
        db.commit()
        return _redirect_to_group(group)
    finally:
        db.close()


@router.post("/yorum/{review_id}/sil")
def delete_review(review_id: int, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        review = db.query(ProductReview).filter(ProductReview.id == review_id).first()
        if review is None:
            raise HTTPException(status_code=404, detail="Yorum bulunamadı")
        group = db.query(ProductGroup).filter(ProductGroup.id == review.product_group_id).first()
        if user is None or review.user_id != user.id:
            raise HTTPException(status_code=403, detail="Bu yorumu silemezsin")
        db.delete(review)
        db.commit()
        return _redirect_to_group(group)
    finally:
        db.close()
