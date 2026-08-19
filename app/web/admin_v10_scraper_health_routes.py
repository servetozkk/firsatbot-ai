from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.scraper_resilience_service import all_store_health, clear_dead_letters, read_dead_letters
router=APIRouter(prefix="/admin/v10-scraper-health",tags=["V10 Scraper Sağlığı"])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent/"templates"))
@router.get("",response_class=HTMLResponse)
def page(request:Request,message:str|None=None):
    health=all_store_health(); dlq=read_dead_letters(300)
    return templates.TemplateResponse(request=request,name="admin_v10_scraper_health.html",context={"health":health,"dead_letters":dlq,"message":message,"open_circuit_count":sum(1 for x in health if x["status"]=="CIRCUIT_OPEN"),"healthy_count":sum(1 for x in health if x["status"]=="HEALTHY")})
@router.post("/clear-dead-letters")
def clear():
    count=clear_dead_letters(); return RedirectResponse("/admin/v10-scraper-health?message="+quote(f"{count} kayıt temizlendi."),status_code=303)
