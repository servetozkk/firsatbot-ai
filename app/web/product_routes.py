from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func

from app.database.database import SessionLocal
from app.database.models import ProductFeature


router = APIRouter(
    prefix="/admin/product-features",
    tags=["Ürün Özellikleri"],
)


BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates"),
)


ALLOWED_VALUE_TYPES = {
    "text",
    "number",
    "boolean",
}

ALLOWED_COMPARISON_TYPES = {
    "higher_better",
    "lower_better",
    "yes_better",
    "no_better",
    "neutral",
}


def normalize_code(value: str) -> str:
    cleaned = value.strip().lower()

    replacements = {
        " ": "_",
        "-": "_",
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }

    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)

    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")

    return cleaned.strip("_")


def validate_feature_form(
    *,
    category: str,
    code: str,
    name: str,
    value_type: str,
    comparison_type: str,
) -> None:
    if not category.strip():
        raise HTTPException(
            status_code=400,
            detail="Kategori alanı zorunludur.",
        )

    if not code.strip():
        raise HTTPException(
            status_code=400,
            detail="Özellik kodu zorunludur.",
        )

    if not name.strip():
        raise HTTPException(
            status_code=400,
            detail="Özellik adı zorunludur.",
        )

    if value_type not in ALLOWED_VALUE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Geçersiz değer türü.",
        )

    if comparison_type not in ALLOWED_COMPARISON_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Geçersiz karşılaştırma türü.",
        )


@router.get(
    "",
    response_class=HTMLResponse,
)
@router.get(
    "/",
    response_class=HTMLResponse,
)
def feature_list(
    request: Request,
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    db = SessionLocal()

    try:
        query = db.query(ProductFeature)

        cleaned_category = (
            category.strip()
            if category
            else ""
        )

        cleaned_search = (
            search.strip()
            if search
            else ""
        )

        if cleaned_category:
            query = query.filter(
                ProductFeature.category
                == cleaned_category
            )

        if cleaned_search:
            pattern = f"%{cleaned_search}%"

            query = query.filter(
                (
                    ProductFeature.name.ilike(pattern)
                )
                | (
                    ProductFeature.code.ilike(pattern)
                )
                | (
                    ProductFeature.section.ilike(pattern)
                )
            )

        features = (
            query
            .order_by(
                ProductFeature.category.asc(),
                ProductFeature.section.asc(),
                ProductFeature.sort_order.asc(),
                ProductFeature.name.asc(),
            )
            .all()
        )

        categories = [
            row[0]
            for row in (
                db.query(ProductFeature.category)
                .distinct()
                .order_by(ProductFeature.category.asc())
                .all()
            )
        ]

        total_count = db.query(
            func.count(ProductFeature.id)
        ).scalar() or 0

        active_count = (
            db.query(func.count(ProductFeature.id))
            .filter(ProductFeature.is_active.is_(True))
            .scalar()
            or 0
        )

        return templates.TemplateResponse(
            request=request,
            name="product_features.html",
            context={
                "features": features,
                "categories": categories,
                "selected_category": cleaned_category,
                "search": cleaned_search,
                "total_count": total_count,
                "active_count": active_count,
            },
        )

    finally:
        db.close()


@router.get(
    "/new",
    response_class=HTMLResponse,
)
def feature_create_form(
    request: Request,
    category: Optional[str] = Query(default=None),
):
    return templates.TemplateResponse(
        request=request,
        name="product_feature_form.html",
        context={
            "feature": None,
            "default_category": category or "",
            "form_action": "/admin/product-features/new",
            "page_title": "Yeni özellik ekle",
        },
    )


@router.post("/new")
def feature_create(
    category: str = Form(...),
    code: str = Form(...),
    name: str = Form(...),
    section: str = Form(default=""),
    unit: str = Form(default=""),
    value_type: str = Form(default="text"),
    comparison_type: str = Form(default="neutral"),
    sort_order: int = Form(default=0),
    is_active: Optional[str] = Form(default=None),
):
    db = SessionLocal()

    try:
        cleaned_category = category.strip()
        cleaned_code = normalize_code(code)
        cleaned_name = name.strip()

        validate_feature_form(
            category=cleaned_category,
            code=cleaned_code,
            name=cleaned_name,
            value_type=value_type,
            comparison_type=comparison_type,
        )

        duplicate = (
            db.query(ProductFeature)
            .filter(
                ProductFeature.category
                == cleaned_category,
                ProductFeature.code
                == cleaned_code,
            )
            .first()
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Bu kategoride aynı özellik kodu "
                    "zaten kayıtlı."
                ),
            )

        feature = ProductFeature(
            category=cleaned_category,
            code=cleaned_code,
            name=cleaned_name,
            section=section.strip() or None,
            unit=unit.strip() or None,
            value_type=value_type,
            comparison_type=comparison_type,
            sort_order=sort_order,
            is_active=(is_active == "on"),
        )

        db.add(feature)
        db.commit()

        return RedirectResponse(
            url=(
                "/admin/product-features"
                f"?category={cleaned_category}"
            ),
            status_code=303,
        )

    finally:
        db.close()


@router.get(
    "/{feature_id}/edit",
    response_class=HTMLResponse,
)
def feature_edit_form(
    request: Request,
    feature_id: int,
):
    db = SessionLocal()

    try:
        feature = (
            db.query(ProductFeature)
            .filter(ProductFeature.id == feature_id)
            .first()
        )

        if feature is None:
            raise HTTPException(
                status_code=404,
                detail="Özellik bulunamadı.",
            )

        return templates.TemplateResponse(
            request=request,
            name="product_feature_form.html",
            context={
                "feature": feature,
                "default_category": feature.category,
                "form_action": (
                    f"/admin/product-features/"
                    f"{feature.id}/edit"
                ),
                "page_title": "Özelliği düzenle",
            },
        )

    finally:
        db.close()


@router.post("/{feature_id}/edit")
def feature_edit(
    feature_id: int,
    category: str = Form(...),
    code: str = Form(...),
    name: str = Form(...),
    section: str = Form(default=""),
    unit: str = Form(default=""),
    value_type: str = Form(default="text"),
    comparison_type: str = Form(default="neutral"),
    sort_order: int = Form(default=0),
    is_active: Optional[str] = Form(default=None),
):
    db = SessionLocal()

    try:
        feature = (
            db.query(ProductFeature)
            .filter(ProductFeature.id == feature_id)
            .first()
        )

        if feature is None:
            raise HTTPException(
                status_code=404,
                detail="Özellik bulunamadı.",
            )

        cleaned_category = category.strip()
        cleaned_code = normalize_code(code)
        cleaned_name = name.strip()

        validate_feature_form(
            category=cleaned_category,
            code=cleaned_code,
            name=cleaned_name,
            value_type=value_type,
            comparison_type=comparison_type,
        )

        duplicate = (
            db.query(ProductFeature)
            .filter(
                ProductFeature.category
                == cleaned_category,
                ProductFeature.code
                == cleaned_code,
                ProductFeature.id != feature_id,
            )
            .first()
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Bu kategoride aynı özellik kodu "
                    "zaten kayıtlı."
                ),
            )

        feature.category = cleaned_category
        feature.code = cleaned_code
        feature.name = cleaned_name
        feature.section = section.strip() or None
        feature.unit = unit.strip() or None
        feature.value_type = value_type
        feature.comparison_type = comparison_type
        feature.sort_order = sort_order
        feature.is_active = is_active == "on"

        db.commit()

        return RedirectResponse(
            url=(
                "/admin/product-features"
                f"?category={cleaned_category}"
            ),
            status_code=303,
        )

    finally:
        db.close()


@router.post("/{feature_id}/toggle")
def feature_toggle(
    feature_id: int,
):
    db = SessionLocal()

    try:
        feature = (
            db.query(ProductFeature)
            .filter(ProductFeature.id == feature_id)
            .first()
        )

        if feature is None:
            raise HTTPException(
                status_code=404,
                detail="Özellik bulunamadı.",
            )

        feature.is_active = not feature.is_active
        category = feature.category

        db.commit()

        return RedirectResponse(
            url=(
                "/admin/product-features"
                f"?category={category}"
            ),
            status_code=303,
        )

    finally:
        db.close()
