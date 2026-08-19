from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.catalog_scan_plan_service import (
    get_active_catalog_plans,
    get_catalog_plans,
)
from app.services.v9_catalog_ingestion_service import (
    get_schedule_state,
    ingestion_history,
    run_all_active_plans,
    run_plan_by_id,
)
from app.services.v9_ingestion_runtime import (
    ensure_v9_ingestion_scheduler,
    v9_ingestion_scheduler_status,
)


router = APIRouter(
    prefix="/admin/v9-ingestion",
    tags=["V9 Katalog Besleme"],
)
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="v9-ingestion-admin",
)
_TASKS: dict[str, dict] = {}

# Router uygulama başlangıcında import edilir; bağımsız scheduler burada
# idempotent biçimde başlatılır.
ensure_v9_ingestion_scheduler()


def _start(fn, title: str) -> dict:
    task_id = str(uuid4())
    _TASKS[task_id] = {
        "id": task_id,
        "title": title,
        "status": "queued",
        "message": "Görev sıraya alındı.",
        "result": None,
        "error": None,
    }

    def runner():
        task = _TASKS[task_id]
        task["status"] = "running"
        task["message"] = "Kataloglar taranıyor."
        try:
            task["result"] = fn()
            task["status"] = "completed"
            task["message"] = "Tarama ve uzlaştırma tamamlandı."
        except Exception as error:
            task["status"] = "failed"
            task["error"] = f"{type(error).__name__}: {error}"
            task["message"] = "Görev başarısız oldu."

    _EXECUTOR.submit(runner)
    return _TASKS[task_id]


@router.get("", response_class=HTMLResponse)
def ingestion_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_v9_ingestion.html",
        context={
            "plans": get_catalog_plans(),
            "state": get_schedule_state(),
            "history": ingestion_history(25),
            "scheduler_status": v9_ingestion_scheduler_status(),
        },
    )


@router.post("/run-all")
def run_all():
    if not get_active_catalog_plans():
        raise HTTPException(
            status_code=400,
            detail="Aktif katalog planı bulunamadı.",
        )
    return JSONResponse(
        {
            "success": True,
            "task": _start(
                run_all_active_plans,
                "Tüm aktif kataloglar",
            ),
        }
    )


@router.post("/{plan_id}/run")
def run_plan(plan_id: str):
    return JSONResponse(
        {
            "success": True,
            "task": _start(
                lambda: run_plan_by_id(plan_id),
                f"Katalog {plan_id}",
            ),
        }
    )


@router.get("/tasks/{task_id}")
def task_status(task_id: str):
    task = _TASKS.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Görev bulunamadı.",
        )
    return {"success": True, "task": task}
