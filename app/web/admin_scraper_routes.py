from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.category_scrapers.registry import CategoryScraperRegistry
from app.services.category_scan_manager import HISTORY_PATH, category_scan_manager
from app.services.category_service import get_categories

router = APIRouter(prefix="/admin/scrapers", tags=["Admin Tarama Merkezi"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _store_code_from_url(url: str) -> str:
    host = urlparse(str(url or "")).netloc.lower()
    if "trendyol" in host:
        return "trendyol"
    if "hepsiburada" in host:
        return "hepsiburada"
    if "pttavm" in host:
        return "pttavm"
    if "beymen" in host:
        return "beymen"
    if "teknosa" in host:
        return "teknosa"
    if "amazon" in host:
        return "amazon"
    return host.split(".")[-2] if "." in host else (host or "unknown")


def _build_context() -> dict:
    registry = CategoryScraperRegistry()
    categories = get_categories()
    active_categories = [category for category in categories if category.get("active")]
    current_tasks = category_scan_manager.list_tasks(30)
    history = category_scan_manager.get_history(100)

    all_tasks = current_tasks + history
    seen_ids: set[str] = set()
    unique_tasks: list[dict] = []
    for task in all_tasks:
        task_id = str(task.get("id") or "")
        if task_id and task_id in seen_ids:
            continue
        if task_id:
            seen_ids.add(task_id)
        unique_tasks.append(task)

    store_categories: dict[str, list[dict]] = defaultdict(list)
    for category in categories:
        store_categories[_store_code_from_url(category.get("url", ""))].append(category)

    store_stats: dict[str, dict] = {}
    for store in registry.list_stores():
        code = store["code"]
        related = store_categories.get(code, [])
        related_names = {str(item.get("name") or "") for item in related}
        related_history = [
            task for task in unique_tasks
            if str(task.get("category_name") or "") in related_names
        ]
        latest = related_history[0] if related_history else None
        successes = sum(1 for task in related_history if task.get("status") == "completed")
        failures = sum(1 for task in related_history if task.get("status") == "failed")
        finished = successes + failures
        success_rate = round((successes / finished) * 100, 1) if finished else None
        running = next((task for task in current_tasks if task.get("status") == "running" and str(task.get("category_name") or "") in related_names), None)

        if running:
            status = "running"
        elif latest and latest.get("status") == "failed":
            status = "error"
        elif related:
            status = "active"
        else:
            status = "idle"

        store_stats[code] = {
            "code": code,
            "name": store["name"],
            "status": status,
            "category_count": len(related),
            "active_category_count": sum(1 for item in related if item.get("active")),
            "success_rate": success_rate,
            "latest": latest,
            "running": running,
        }

    running_tasks = [task for task in current_tasks if task.get("status") == "running"]
    queued_tasks = [task for task in current_tasks if task.get("status") == "queued"]
    completed_history = [task for task in history if task.get("status") == "completed"]
    failed_history = [task for task in history if task.get("status") == "failed"]

    today = datetime.now().astimezone().date()
    today_tasks = []
    for task in history:
        finished = _parse_datetime(task.get("finished_at"))
        if finished and finished.astimezone().date() == today:
            today_tasks.append(task)

    today_found = sum(int((task.get("result") or {}).get("found_count", 0) or 0) for task in today_tasks)
    today_saved = sum(int((task.get("result") or {}).get("saved_count", 0) or 0) for task in today_tasks)
    error_types = Counter()
    for task in failed_history:
        error = str(task.get("error") or "Bilinmeyen hata")
        error_types[error.split(":", 1)[0]] += 1

    recent_tasks = unique_tasks[:20]
    return {
        "stores": list(store_stats.values()),
        "categories": categories,
        "active_categories": active_categories,
        "running_tasks": running_tasks,
        "queued_tasks": queued_tasks,
        "recent_tasks": recent_tasks,
        "history": history[:20],
        "today_found": today_found,
        "today_saved": today_saved,
        "completed_count": len(completed_history),
        "failed_count": len(failed_history),
        "error_types": error_types.most_common(6),
    }


@router.get("", response_class=HTMLResponse)
def scraper_center(request: Request, message: str | None = None, error: str | None = None):
    context = _build_context()
    context.update({"message": message, "error": error})
    return templates.TemplateResponse(
        request=request,
        name="admin_scraper_center.html",
        context=context,
    )


@router.post("/scan-all")
def start_all_scans():
    try:
        task = category_scan_manager.start_all()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse({"success": True, "task": task})


@router.post("/categories/{category_id}/scan")
def start_single_scan(category_id: str):
    try:
        task = category_scan_manager.start_category(category_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return JSONResponse({"success": True, "task": task})


@router.get("/status")
def scraper_status():
    context = _build_context()
    return {
        "success": True,
        "running_tasks": context["running_tasks"],
        "queued_tasks": context["queued_tasks"],
        "recent_tasks": context["recent_tasks"][:10],
        "today_found": context["today_found"],
        "today_saved": context["today_saved"],
    }


@router.post("/history/clear")
def clear_scan_history():
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.write_text("[]", encoding="utf-8")
    except OSError as error:
        raise HTTPException(status_code=500, detail=f"Tarama geçmişi temizlenemedi: {error}") from error
    return RedirectResponse("/admin/scrapers?message=Tarama%20geçmişi%20temizlendi", status_code=303)
