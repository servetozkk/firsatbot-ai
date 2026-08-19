from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.database.database import SessionLocal
from app.services.sitemap_service import (
    ENGINE_VERSION,
    brand_entries,
    category_entries,
    index_items,
    landing_entries,
    product_entries,
    product_page_count,
    sitemap_index_xml,
    static_entries,
    store_entries,
    urlset_xml,
)

router = APIRouter(tags=["XML Sitemap v13.6.2"])
XML_HEADERS = {"Cache-Control": "public, max-age=900"}


def _xml(content: str) -> Response:
    return Response(content=content, media_type="application/xml; charset=utf-8", headers=XML_HEADERS)


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap_index(request: Request):
    db = SessionLocal()
    try:
        return _xml(sitemap_index_xml(request.base_url, index_items(db)))
    finally:
        db.close()


@router.get("/sitemaps/static.xml", include_in_schema=False)
def static_sitemap(request: Request):
    return _xml(urlset_xml(request.base_url, static_entries()))


@router.get("/sitemaps/categories.xml", include_in_schema=False)
def categories_sitemap(request: Request):
    db = SessionLocal()
    try:
        return _xml(urlset_xml(request.base_url, category_entries(db)))
    finally:
        db.close()


@router.get("/sitemaps/brands.xml", include_in_schema=False)
def brands_sitemap(request: Request):
    db = SessionLocal()
    try:
        return _xml(urlset_xml(request.base_url, brand_entries(db)))
    finally:
        db.close()


@router.get("/sitemaps/stores.xml", include_in_schema=False)
def stores_sitemap(request: Request):
    db = SessionLocal()
    try:
        return _xml(urlset_xml(request.base_url, store_entries(db)))
    finally:
        db.close()


@router.get("/sitemaps/landings.xml", include_in_schema=False)
def landings_sitemap(request: Request):
    return _xml(urlset_xml(request.base_url, landing_entries()))


@router.get("/sitemaps/products-{page}.xml", include_in_schema=False)
def products_sitemap(request: Request, page: int):
    db = SessionLocal()
    try:
        if page < 1 or page > product_page_count(db):
            raise HTTPException(status_code=404, detail="Sitemap parçası bulunamadı")
        return _xml(urlset_xml(request.base_url, product_entries(db, page)))
    finally:
        db.close()


@router.get("/api/sitemap/v13")
def sitemap_metadata():
    db = SessionLocal()
    try:
        return {
            "engine_version": ENGINE_VERSION,
            "read_only": True,
            "index_url": "/sitemap.xml",
            "product_sitemap_count": product_page_count(db),
            "sitemaps": [path for path, _ in index_items(db)],
        }
    finally:
        db.close()
