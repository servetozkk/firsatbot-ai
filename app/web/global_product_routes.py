from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.database.database import SessionLocal
from app.database.models import ProductGroup
from app.services.comparison_service import get_product_comparison
from app.services.smart_recommendation_service import get_smart_recommendations
from app.web.product_group_routes import product_group_detail
from app.services.seo_url_service import parse_product_path, product_url


router = APIRouter(prefix="/urun", tags=["Global Ürün Deneyimi"])


@router.get("/{identity_key}/alternatifler", response_class=JSONResponse)
def global_product_alternatives(identity_key: str, limit: int = 4):
    """Global katalogdan teknik özellik farkındalıklı alternatifleri döndürür."""
    db = SessionLocal()
    try:
        group = db.query(ProductGroup).filter(ProductGroup.group_key == identity_key).first()
        if group is None:
            raise HTTPException(status_code=404, detail="Global ürün bulunamadı")
        comparison = get_product_comparison(db=db, identity_key=identity_key)
        if not comparison:
            raise HTTPException(status_code=404, detail="Aktif ürün teklifi bulunamadı")
        safe_limit = max(1, min(int(limit or 4), 12))
        buckets = get_smart_recommendations(
            db=db,
            current_group=group,
            current_comparison=comparison,
            per_bucket=safe_limit,
        )
        return {
            "identity_key": identity_key,
            "engine_version": "13.2.2",
            "read_only": True,
            "buckets": buckets,
        }
    finally:
        db.close()


@router.get("/{identity_key}", response_class=HTMLResponse)
def global_product_detail(
    request: Request,
    identity_key: str,
    variant: int | None = None,
    firsat_session: str | None = Cookie(default=None),
):
    """Akakçe tipi tek global ürün sayfasının SEO dostu kanonik URL girişidir."""
    lookup_key, requested_slug = parse_product_path(identity_key)
    db = SessionLocal()
    try:
        group = db.query(ProductGroup).filter(ProductGroup.group_key == lookup_key).first()
        if group is None:
            raise HTTPException(status_code=404, detail="Global ürün bulunamadı")
        canonical_path = product_url(group.canonical_name, group.group_key)
    finally:
        db.close()
    requested_path = "/urun/" + identity_key
    if requested_path != canonical_path:
        suffix = f"?variant={variant}" if variant is not None else ""
        return RedirectResponse(url=canonical_path + suffix, status_code=301)
    return product_group_detail(
        request=request,
        identity_key=lookup_key,
        variant=variant,
        firsat_session=firsat_session,
    )
