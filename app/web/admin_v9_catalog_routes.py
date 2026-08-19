from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, RawProduct
from app.services.catalog_reconciliation_service import (
    process_reconciliation_queue,
    reconciliation_summary,
)


router = APIRouter(prefix="/admin/v9-catalog", tags=["V9 Global Katalog"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("", response_class=HTMLResponse)
def v9_catalog_page(
    request: Request,
    message: str | None = None,
):
    with SessionLocal() as db:
        summary = reconciliation_summary(db)
        raw_rows = (
            db.query(RawProduct)
            .order_by(RawProduct.id.desc())
            .limit(100)
            .all()
        )
        products = (
            db.query(GlobalProduct)
            .order_by(
                GlobalProduct.active_offer_count.desc(),
                GlobalProduct.id.desc(),
            )
            .limit(100)
            .all()
        )
        offers = (
            db.query(GlobalOffer)
            .filter(
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
                GlobalOffer.lifecycle_status == "ACTIVE",
            )
            .order_by(GlobalOffer.updated_at.desc())
            .limit(100)
            .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="admin_v9_catalog.html",
        context={
            "summary": summary,
            "raw_rows": raw_rows,
            "products": products,
            "offers": offers,
            "message": message,
        },
    )


@router.post("/reconcile")
def reconcile_pending():
    with SessionLocal() as db:
        result = process_reconciliation_queue(
            db=db,
            limit=1000,
            retry_failed=False,
        )
    message = (
        f"{result['processed']} ham kayıt işlendi; "
        f"{result['matched']} eşleşti, {result['failed']} hata."
    )
    return RedirectResponse(
        f"/admin/v9-catalog?message={message}",
        status_code=303,
    )


@router.post("/retry-failed")
def retry_failed():
    with SessionLocal() as db:
        result = process_reconciliation_queue(
            db=db,
            limit=1000,
            retry_failed=True,
        )
    message = (
        f"{result['processed']} kayıt yeniden işlendi; "
        f"{result['matched']} eşleşti, {result['failed']} hata."
    )
    return RedirectResponse(
        f"/admin/v9-catalog?message={message}",
        status_code=303,
    )
