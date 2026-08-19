from __future__ import annotations
import os
from datetime import datetime, timezone
from urllib.parse import quote
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response
from app.database.database import SessionLocal
from app.database.models import ProductGroup

router = APIRouter(include_in_schema=False)

def _base_url(request: Request) -> str:
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    return configured or str(request.base_url).rstrip("/")

@router.get("/robots.txt", response_class=PlainTextResponse)
def robots(request: Request) -> str:
    base = _base_url(request)
    return "\n".join(["User-agent: *", "Allow: /", "Disallow: /admin", "Disallow: /api/", "Disallow: /hesabim", "Disallow: /bildirimler", "Disallow: /bildirim-ayarlari", f"Sitemap: {base}/sitemap.xml", ""])

@router.get("/sitemap.xml")
def sitemap(request: Request) -> Response:
    base = _base_url(request)
    static_urls = [("/", "daily", "1.0"), ("/arama", "daily", "0.9"), ("/kategoriler", "daily", "0.8"), ("/firsatlar", "hourly", "0.9"), ("/fiyati-dusenler", "hourly", "0.9"), ("/ai-tavsiyeleri", "daily", "0.8")]
    entries = [f"<url><loc>{base}{path}</loc><changefreq>{freq}</changefreq><priority>{priority}</priority></url>" for path, freq, priority in static_urls]
    db = SessionLocal()
    try:
        groups = db.query(ProductGroup).order_by(ProductGroup.updated_at.desc(), ProductGroup.id.desc()).limit(5000).all()
        for group in groups:
            key = quote(str(group.group_key), safe="")
            updated = getattr(group, "updated_at", None)
            if updated:
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                lastmod = updated.date().isoformat()
            else:
                lastmod = datetime.now(timezone.utc).date().isoformat()
            entries.append(f"<url><loc>{base}/karsilastir/{key}</loc><lastmod>{lastmod}</lastmod><changefreq>daily</changefreq><priority>0.7</priority></url>")
    finally:
        db.close()
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(entries) + "</urlset>"
    return Response(content=xml, media_type="application/xml")
