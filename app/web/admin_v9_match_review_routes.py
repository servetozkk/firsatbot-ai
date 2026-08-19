from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.database.models import GlobalProduct, RawProduct
from app.database.v9_models import ProductMatchReview
from app.services.v9_match_review_service import approve_match_review, reject_match_review


router = APIRouter(prefix="/admin/v9-match-reviews", tags=["V9 Eşleşme İnceleme"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _decode(value: str | None):
    try:
        return json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []


@router.get("", response_class=HTMLResponse)
def match_review_page(request: Request, message: str | None = None, error: str | None = None):
    with SessionLocal() as db:
        rows = (
            db.query(ProductMatchReview, RawProduct, GlobalProduct)
            .join(RawProduct, RawProduct.id == ProductMatchReview.raw_product_id)
            .outerjoin(GlobalProduct, GlobalProduct.id == ProductMatchReview.candidate_global_product_id)
            .filter(ProductMatchReview.status == "PENDING")
            .order_by(ProductMatchReview.confidence.desc(), ProductMatchReview.id.asc())
            .limit(300)
            .all()
        )
        reviews = [{
            "review": review,
            "raw": raw,
            "candidate": candidate,
            "reasons": _decode(review.reasons_json),
            "conflicts": _decode(review.conflicts_json),
            "identifiers": _decode(review.identifiers_json),
        } for review, raw, candidate in rows]

    return templates.TemplateResponse(
        request=request,
        name="admin_v9_match_reviews.html",
        context={"reviews": reviews, "message": message, "error": error},
    )


@router.post("/{review_id}/approve")
def approve(review_id: int):
    with SessionLocal() as db:
        success, message = approve_match_review(db=db, review_id=review_id)
    key = "message" if success else "error"
    return RedirectResponse(f"/admin/v9-match-reviews?{key}={quote(message)}", status_code=303)


@router.post("/{review_id}/reject")
def reject(review_id: int):
    with SessionLocal() as db:
        success, message = reject_match_review(db=db, review_id=review_id)
    key = "message" if success else "error"
    return RedirectResponse(f"/admin/v9-match-reviews?{key}={quote(message)}", status_code=303)
