from pathlib import Path
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.services.bulk_identity_service import identity_status, init_bulk_identity_schema, process_match_queue

router = APIRouter(tags=["Toplu Kimlik v14.3"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/admin/bulk-identity", response_class=HTMLResponse)
def page(request: Request):
    init_bulk_identity_schema()
    return templates.TemplateResponse(request=request, name="admin_bulk_identity.html", context={"status": identity_status()})

@router.get("/api/bulk-identity/v14/status")
def status():
    return identity_status()

@router.post("/api/bulk-identity/v14/process")
def process(limit: int = Query(250, ge=1, le=2000)):
    return JSONResponse({"success": True, "result": process_match_queue(limit), "status": identity_status()})
