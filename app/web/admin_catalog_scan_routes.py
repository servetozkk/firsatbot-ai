from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import HTMLResponse,JSONResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from app.category_scrapers.registry import CategoryScraperRegistry
from app.services.catalog_scan_manager import catalog_scan_manager
from app.services.catalog_scan_plan_service import create_catalog_plan,delete_catalog_plan,get_catalog_plans,set_catalog_plan_active
router=APIRouter(prefix="/admin/catalog-scans",tags=["Admin Katalog Tarama"])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent/"templates"))
@router.get("",response_class=HTMLResponse)
def page(request:Request,message:str|None=None,error:str|None=None):
    return templates.TemplateResponse(request=request,name="admin_catalog_scans.html",context={"plans":get_catalog_plans(),"stores":CategoryScraperRegistry().list_stores(),"history":catalog_scan_manager.history(15),"message":message,"error":error})
@router.post("/create")
async def create(request:Request):
    f=await request.form(); stores=CategoryScraperRegistry().list_stores()
    urls={s["code"]:str(f.get("url_"+s["code"],"") or "") for s in stores}
    ok,msg,_=create_catalog_plan(str(f.get("name","")),int(f.get("limit",100)),int(f.get("interval_minutes",60)),str(f.get("active","")).lower() in {"true","1","on","yes"},urls)
    return RedirectResponse(f"/admin/catalog-scans?{'message' if ok else 'error'}={quote(msg)}",status_code=303)
@router.post("/{id}/toggle")
async def toggle(id:str,request:Request):
    f=await request.form();ok,msg=set_catalog_plan_active(id,str(f.get("active","")).lower() in {"true","1","on","yes"})
    return RedirectResponse(f"/admin/catalog-scans?{'message' if ok else 'error'}={quote(msg)}",status_code=303)
@router.post("/{id}/delete")
def delete(id:str):
    ok,msg=delete_catalog_plan(id)
    if not ok:raise HTTPException(404,msg)
    return RedirectResponse("/admin/catalog-scans?message="+quote(msg),status_code=303)
@router.post("/{id}/scan")
def scan(id:str):
    try:t=catalog_scan_manager.start_plan(id)
    except ValueError as e:raise HTTPException(400,str(e))
    return JSONResponse({"success":True,"task":t})
@router.post("/scan-all")
def scan_all():
    try:t=catalog_scan_manager.start_all()
    except ValueError as e:raise HTTPException(400,str(e))
    return JSONResponse({"success":True,"task":t})
@router.get("/tasks/{id}")
def task(id:str):
    t=catalog_scan_manager.get_task(id)
    if not t:raise HTTPException(404,"Görev bulunamadı.")
    return {"success":True,"task":t}
