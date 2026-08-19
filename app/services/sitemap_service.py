from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import ceil
from typing import Iterable
from xml.sax.saxutils import escape

from app.services.seo_url_service import product_url, slugify

ENGINE_VERSION = "13.6.4"
PRODUCTS_PER_SITEMAP = 10000


@dataclass(frozen=True)
class SitemapEntry:
    path: str
    lastmod: datetime | date | str | None = None
    changefreq: str | None = None
    priority: float | None = None


def _absolute(base_url: object, path: object) -> str:
    root = str(base_url).rstrip("/")
    value = str(path or "").strip()
    if value.startswith(("http://", "https://")):
        return value
    return root + "/" + value.lstrip("/")


def _lastmod(value: datetime | date | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def urlset_xml(base_url: object, entries: Iterable[SitemapEntry]) -> str:
    rows = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for entry in entries:
        rows.append("  <url>")
        rows.append(f"    <loc>{escape(_absolute(base_url, entry.path))}</loc>")
        modified = _lastmod(entry.lastmod)
        if modified:
            rows.append(f"    <lastmod>{escape(modified)}</lastmod>")
        if entry.changefreq:
            rows.append(f"    <changefreq>{escape(entry.changefreq)}</changefreq>")
        if entry.priority is not None:
            rows.append(f"    <priority>{max(0.0, min(1.0, float(entry.priority))):.1f}</priority>")
        rows.append("  </url>")
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


def sitemap_index_xml(base_url: object, paths: Iterable[tuple[str, datetime | date | str | None]]) -> str:
    rows = ['<?xml version="1.0" encoding="UTF-8"?>', '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod in paths:
        rows.append("  <sitemap>")
        rows.append(f"    <loc>{escape(_absolute(base_url, path))}</loc>")
        modified = _lastmod(lastmod)
        if modified:
            rows.append(f"    <lastmod>{escape(modified)}</lastmod>")
        rows.append("  </sitemap>")
    rows.append("</sitemapindex>")
    return "\n".join(rows) + "\n"


def static_entries() -> list[SitemapEntry]:
    return [
        SitemapEntry("/", changefreq="daily", priority=1.0),
        SitemapEntry("/arama", changefreq="daily", priority=0.8),
        SitemapEntry("/kategoriler", changefreq="daily", priority=0.9),
        SitemapEntry("/markalar", changefreq="weekly", priority=0.8),
        SitemapEntry("/magazalar", changefreq="daily", priority=0.8),
        SitemapEntry("/kampanyalar", changefreq="hourly", priority=0.8),
        SitemapEntry("/kuponlar", changefreq="hourly", priority=0.8),
        SitemapEntry("/stok", changefreq="hourly", priority=0.7),
        SitemapEntry("/yeni-urunler", changefreq="daily", priority=0.8),
        SitemapEntry("/karsilastir", changefreq="weekly", priority=0.5),
        SitemapEntry("/kesfet", changefreq="weekly", priority=0.8),
    ]



def landing_entries() -> list[SitemapEntry]:
    from app.services.landing_page_service import list_landings
    return [SitemapEntry(item["url"], changefreq="daily", priority=0.8) for item in list_landings()]


def product_count(db) -> int:
    from sqlalchemy import func
    from app.database.models import ProductGroup
    return int(db.query(func.count(ProductGroup.id)).scalar() or 0)


def product_page_count(db) -> int:
    return max(1, ceil(product_count(db) / PRODUCTS_PER_SITEMAP))


def product_entries(db, page: int) -> list[SitemapEntry]:
    from app.database.models import ProductGroup
    page = max(1, int(page))
    rows = (
        db.query(ProductGroup)
        .order_by(ProductGroup.id.asc())
        .offset((page - 1) * PRODUCTS_PER_SITEMAP)
        .limit(PRODUCTS_PER_SITEMAP)
        .all()
    )
    return [
        SitemapEntry(
            product_url(group.canonical_name, group.group_key),
            lastmod=group.updated_at or group.created_at,
            changefreq="daily",
            priority=0.9,
        )
        for group in rows
        if str(group.group_key or "").strip()
    ]


def category_entries(db) -> list[SitemapEntry]:
    from sqlalchemy import func
    from app.database.models import ProductGroup
    rows = (
        db.query(ProductGroup.category, func.max(ProductGroup.updated_at))
        .filter(ProductGroup.category.isnot(None), ProductGroup.category != "")
        .group_by(ProductGroup.category)
        .order_by(ProductGroup.category.asc())
        .all()
    )
    return [SitemapEntry(f"/kategori/{slugify(name)}", lastmod=updated, changefreq="daily", priority=0.8) for name, updated in rows]


def brand_entries(db) -> list[SitemapEntry]:
    from sqlalchemy import func
    from app.database.models import ProductGroup
    rows = (
        db.query(ProductGroup.brand, func.max(ProductGroup.updated_at))
        .filter(ProductGroup.brand.isnot(None), ProductGroup.brand != "")
        .group_by(ProductGroup.brand)
        .order_by(ProductGroup.brand.asc())
        .all()
    )
    return [SitemapEntry(f"/marka-merkezi/{slugify(name)}", lastmod=updated, changefreq="weekly", priority=0.7) for name, updated in rows]


def store_entries(db) -> list[SitemapEntry]:
    from app.database.models import Store
    rows = db.query(Store).filter(Store.is_active.is_(True)).order_by(Store.name.asc()).all()
    return [
        SitemapEntry(
            f"/magaza-merkezi/{slugify(store.name or store.code)}",
            lastmod=store.updated_at or store.created_at,
            changefreq="daily",
            priority=0.7,
        )
        for store in rows
    ]


def index_items(db) -> list[tuple[str, datetime | date | str | None]]:
    from sqlalchemy import func
    from app.database.models import ProductGroup, Store
    latest_product = db.query(func.max(ProductGroup.updated_at)).scalar()
    latest_store = db.query(func.max(Store.updated_at)).scalar()
    items: list[tuple[str, datetime | date | str | None]] = [
        ("/sitemaps/static.xml", None),
        ("/sitemaps/categories.xml", latest_product),
        ("/sitemaps/brands.xml", latest_product),
        ("/sitemaps/stores.xml", latest_store),
        ("/sitemaps/landings.xml", None),
    ]
    for page in range(1, product_page_count(db) + 1):
        items.append((f"/sitemaps/products-{page}.xml", latest_product))
    return items
