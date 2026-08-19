from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_

from app.database.database import SessionLocal
from app.database.models import ProductDB
from app.services.data_integrity_service import record_admin_action
from app.services.identity_audit_service import (
    apply_identity_updates,
    audit_products,
    build_duplicate_clusters,
)

router = APIRouter(prefix="/admin/identity", tags=["Product Identity"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("", response_class=HTMLResponse)
def identity_center(
    request: Request,
    q: str = Query(default=""),
    status: str = Query(default=""),
    duplicate: str = Query(default=""),
):
    with SessionLocal() as session:
        query = session.query(ProductDB).filter(ProductDB.is_deleted.is_(False))
        if q:
            term = f"%{q.strip()}%"
            query = query.filter(or_(
                ProductDB.name.ilike(term), ProductDB.brand.ilike(term),
                ProductDB.model.ilike(term), ProductDB.product_code.ilike(term),
            ))
        products = query.order_by(ProductDB.updated_at.desc(), ProductDB.id.desc()).limit(1000).all()
        all_rows = audit_products(session, products)
        duplicate_clusters = build_duplicate_clusters(all_rows)
        duplicate_ids = {item.product_id for cluster in duplicate_clusters for item in cluster["items"]}
        rows = all_rows
        if status in {"strong", "review", "weak"}:
            rows = [row for row in rows if row.status == status]
        if duplicate == "yes":
            rows = [row for row in rows if row.product_id in duplicate_ids]
        stats = {
            "total": len(all_rows),
            "strong": sum(row.status == "strong" for row in all_rows),
            "review": sum(row.status == "review" for row in all_rows),
            "weak": sum(row.status == "weak" for row in all_rows),
            "duplicates": len(duplicate_clusters),
            "cross_group_duplicates": sum(cluster["needs_merge"] for cluster in duplicate_clusters),
            "average": round(sum(row.confidence for row in all_rows) / len(all_rows)) if all_rows else 0,
        }
    return templates.TemplateResponse(request=request, name="admin_identity_center.html", context={
        "rows": rows[:400], "stats": stats, "q": q, "status": status,
        "duplicate": duplicate, "duplicate_clusters": duplicate_clusters[:30],
    })


@router.post("/apply")
def identity_apply(
    product_ids: list[int] = Form(default=[]),
    return_q: str = Form(default=""),
    return_status: str = Form(default=""),
):
    with SessionLocal() as session:
        stats = apply_identity_updates(session, product_ids)
        record_admin_action(session, action="identity_recalculate", details={"product_ids": product_ids, **stats})
        session.commit()
    query = urlencode({"q": return_q, "status": return_status, "updated": stats["updated"]})
    return RedirectResponse(f"/admin/identity?{query}", status_code=303)
