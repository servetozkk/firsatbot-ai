from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(tags=["Admin Modül Merkezi"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)

_LABELS = {
    "/admin": ("Dashboard", "Ana yönetim ekranı", "Genel"),
    "/admin/catalog": ("Katalog Merkezi", "Ürün ve katalog yönetimi", "Katalog"),
    "/admin/products": ("Ürünler", "Ürün kayıtlarını yönet", "Katalog"),
    "/admin/offers": ("Teklifler", "Mağaza tekliflerini yönet", "Katalog"),
    "/admin/catalog-scans": ("Katalog Taramaları", "Kategori bazlı otomatik taramalar", "Operasyon"),
    "/admin/bulk-catalog": ("Toplu Katalog", "Akakçe tipi toplu katalog motoru", "Operasyon"),
    "/admin/bulk-identity": ("Toplu Kimlik Motoru", "Staging ürünlerini global ürünlere bağla", "Global Katalog"),
    "/admin/live-prices": ("Canlı Fiyat Motoru", "Aktif teklif fiyatlarını yeniden kontrol et", "Operasyon"),
    "/admin/scraper-operations": ("Scraper Operasyonları", "Scraper düzeltmeleri ve sağlık durumu", "Operasyon"),
    "/admin/scrapers": ("Tarama Merkezi", "Mağaza scraper yönetimi", "Operasyon"),
    "/admin/ai-comparison": ("AI Karşılaştırma", "Eşleşme güveni ve veri kalite analizi", "AI & Analiz"),
    "/admin/data-quality": ("Veri Kalitesi", "Ürün ve teklif veri kalitesi", "AI & Analiz"),
    "/admin/identity": ("Kimlik Merkezi", "Ürün kimliklerini incele", "Global Katalog"),
    "/admin/matching": ("Ürün Eşleştirme", "Ürün gruplarını ve eşleşmeleri yönet", "Global Katalog"),
    "/admin/v9-catalog": ("Global Katalog", "Global ürün ve varyant görünümü", "Global Katalog"),
    "/admin/v9-ingestion": ("Katalog Besleme", "Ham katalog besleme işlemleri", "Operasyon"),
    "/admin/v9-match-reviews": ("Eşleşme İnceleme", "Şüpheli eşleşmeleri incele", "Global Katalog"),
    "/admin/alerts": ("Alarm Merkezi", "Fiyat ve stok alarmları", "Topluluk"),
    "/admin/analytics": ("Kullanıcı Analitiği", "Anonim kullanıcı hareketleri", "AI & Analiz"),
    "/admin/reports": ("Raporlar", "Sistem ve iş raporları", "Analiz & Sistem"),
    "/admin/v9-performance": ("Performans", "Sorgu ve sistem performansı", "Analiz & Sistem"),
    "/admin/production-release": ("Production Durumu", "Canlı yayın hazırlığı", "Analiz & Sistem"),
    "/admin/public-beta": ("Public Beta", "Public beta durumu ve geri bildirimler", "Analiz & Sistem"),
    "/admin/beta": ("Beta Sağlığı", "Modül ve beta hazırlık kontrolleri", "Analiz & Sistem"),
    "/admin/v10-security": ("Güvenlik", "Güvenlik ve yedekleme kontrolleri", "Analiz & Sistem"),
    "/admin/settings": ("Ayarlar", "Uygulama ayarları", "Analiz & Sistem"),
}


def _route_methods(route: APIRoute) -> set[str]:
    return {method.upper() for method in (route.methods or set())}


def _is_openable_admin_route(route: APIRoute) -> bool:
    path = route.path
    if not path.startswith("/admin"):
        return False
    if "GET" not in _route_methods(route):
        return False
    if "{" in path:
        return False
    if path in {"/admin/access", "/admin/access/logout"}:
        return False
    return True


def _humanize(path: str) -> str:
    name = path.rstrip("/").split("/")[-1] or "dashboard"
    return name.replace("-", " ").replace("_", " ").title()


def discover_admin_modules(request: Request) -> dict[str, list[dict[str, Any]]]:
    unique: dict[str, dict[str, Any]] = {}
    for route in request.app.routes:
        if not isinstance(route, APIRoute) or not _is_openable_admin_route(route):
            continue
        path = route.path.rstrip("/") or "/admin"
        title, description, group = _LABELS.get(
            path,
            (_humanize(path), "Yönetim modülü", "Diğer Modüller"),
        )
        unique[path] = {
            "path": path,
            "title": title,
            "description": description,
            "group": group,
            "route_name": route.name,
        }

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    group_order = [
        "Genel",
        "Katalog",
        "Operasyon",
        "Global Katalog",
        "AI & Analiz",
        "Topluluk",
        "Analiz & Sistem",
        "Diğer Modüller",
    ]
    for module in unique.values():
        grouped[module["group"]].append(module)
    for modules in grouped.values():
        modules.sort(key=lambda item: item["title"].casefold())

    return {
        group: grouped[group]
        for group in group_order
        if grouped.get(group)
    }


@router.get("/admin/module-center", response_class=HTMLResponse)
def admin_module_center(request: Request):
    groups = discover_admin_modules(request)
    module_count = sum(len(items) for items in groups.values())
    return templates.TemplateResponse(
        request=request,
        name="admin_module_center_v14.html",
        context={
            "groups": groups,
            "module_count": module_count,
        },
    )


@router.get("/api/admin-modules/v14")
def admin_module_api(request: Request):
    groups = discover_admin_modules(request)
    return {
        "engine_version": "14.7.0",
        "status": "ADMIN_NAVIGATION_READY",
        "module_count": sum(len(items) for items in groups.values()),
        "groups": groups,
    }
