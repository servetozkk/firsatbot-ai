from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.ai_comparison_v14_service import analyze_global_product
from app.services.global_price_experience_v14_service import get_price_history
from app.services.global_marketplace_v14_service import (
    get_global_product,
    list_global_products,
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
router = APIRouter(tags=["Akakçe Tipi Global Fiyat Karşılaştırma"])


def _parse_product_id(value: int | str) -> int:
    """
    125, "125" ve "125-asus-vivobook-..." biçimlerini kabul eder.
    Kimlik her zaman path değerinin başındaki pozitif tam sayıdır.
    """
    if isinstance(value, int):
        if value <= 0:
            raise HTTPException(status_code=404, detail="Geçersiz ürün kimliği")
        return value

    match = re.match(r"^\s*(\d+)(?:-|$)", str(value or ""))
    if not match:
        raise HTTPException(
            status_code=404,
            detail="Ürün adresinden geçerli global ürün kimliği çıkarılamadı",
        )

    product_id = int(match.group(1))
    if product_id <= 0:
        raise HTTPException(status_code=404, detail="Geçersiz ürün kimliği")
    return product_id


def _load_product(product_ref: int | str) -> tuple[int, dict]:
    product_id = _parse_product_id(product_ref)
    product = get_global_product(product_id)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Global ürün veya aktif teklif bulunamadı",
        )
    return product_id, product


def _render_product(
    *,
    request: Request,
    product_id: int,
    product: dict,
):
    canonical_path = (
        f"/fiyat-karsilastirma/global/{product_id}-{product['slug']}"
    )
    product["ai_insight"] = analyze_global_product(product_id)
    product["price_history"] = get_price_history(product_id, days=90)

    return templates.TemplateResponse(
        request=request,
        name="global_marketplace_product_v14.html",
        context={
            "product": product,
            "seo_title": (
                f"{product['canonical_name']} Fiyatları "
                "ve Mağaza Karşılaştırması"
            ),
            "seo_description": (
                f"{product['canonical_name']} için "
                f"{product['store_count']} mağazadaki fiyatları karşılaştırın."
            ),
            "canonical_url": (
                str(request.base_url).rstrip("/") + canonical_path
            ),
        },
    )


@router.get("/fiyat-karsilastirma", response_class=HTMLResponse)
def marketplace_catalog(
    request: Request,
    q: str = Query(default=""),
    brand: str = Query(default=""),
    sort: str = Query(default="popular"),
    page: int = Query(default=1, ge=1),
):
    data = list_global_products(q=q, brand=brand, sort=sort, page=page)
    return templates.TemplateResponse(
        request=request,
        name="global_marketplace_catalog_v14.html",
        context={
            **data,
            "seo_title": "Fiyat Karşılaştırma · FırsatAI",
            "seo_description": (
                "Aynı ürünün farklı mağazalardaki güncel fiyatlarını "
                "tek ekranda karşılaştırın."
            ),
            "canonical_url": str(request.url.replace(query="")),
        },
    )


@router.get(
    "/fiyat-karsilastirma/global/{product_ref}",
    response_class=HTMLResponse,
    name="global_marketplace_product",
)
def marketplace_product(
    request: Request,
    product_ref: str,
):
    product_id, product = _load_product(product_ref)
    canonical_path = (
        f"/fiyat-karsilastirma/global/{product_id}-{product['slug']}"
    )

    # Eksik veya yanlış slug varsa SEO adresine yönlendir.
    if request.url.path != canonical_path:
        return RedirectResponse(url=canonical_path, status_code=301)

    return _render_product(
        request=request,
        product_id=product_id,
        product=product,
    )


@router.get(
    "/fiyat-karsilastirma/{product_ref}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def legacy_marketplace_product(
    request: Request,
    product_ref: str,
):
    """
    Eski /fiyat-karsilastirma/125-asus... bağlantılarını destekler.
    Doğrudan yeni /global/ SEO adresine yönlendirir.
    """
    product_id, product = _load_product(product_ref)
    return RedirectResponse(
        url=f"/fiyat-karsilastirma/global/{product_id}-{product['slug']}",
        status_code=301,
    )


@router.get(
    "/api/global-marketplace/v14/products",
    response_class=JSONResponse,
)
def marketplace_products_api(
    q: str = "",
    brand: str = "",
    sort: str = "popular",
    page: int = 1,
):
    result = list_global_products(
        q=q,
        brand=brand,
        sort=sort,
        page=page,
    )
    return {"engine_version": "14.9.1", **result}


@router.get(
    "/api/global-marketplace/v14/products/{product_ref}/price-history",
    response_class=JSONResponse,
)
def global_product_price_history(
    product_ref: str,
    days: int = Query(default=90, ge=7, le=3650),
):
    product_id = _parse_product_id(product_ref)
    return get_price_history(product_id, days=days)


@router.get(
    "/api/global-marketplace/v14/products/{product_ref}",
    response_class=JSONResponse,
)
def marketplace_product_api(product_ref: str):
    product_id, product = _load_product(product_ref)
    product["ai_insight"] = analyze_global_product(product_id)
    return {
        "engine_version": "14.9.1",
        "product": product,
    }
