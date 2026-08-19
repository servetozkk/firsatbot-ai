from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.services.user_identity_service import resolve_owner_key
from app.services.advanced_alert_service import (ALERT_TYPES, admin_summary, create_alert, delete_alert, ensure_schema, evaluate_alert, events, list_alerts, update_alert)
from pathlib import Path

router=APIRouter(tags=["advanced-alerts-v13"])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parents[1]/"templates"))
class AlertCreate(BaseModel):
    alert_type:str
    global_product_id:int|None=None
    identity_key:str|None=None
    threshold_value:float|None=None
    rule:dict[str,Any]=Field(default_factory=dict)
class AlertUpdate(BaseModel):
    threshold_value:float|None=None
    rule:dict[str,Any]|None=None
    is_active:bool|None=None
class AlertEvaluate(BaseModel): signals:dict[str,Any]=Field(default_factory=dict)
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
def owner(response:Response, db:Session, session:str|None, visitor:str|None):
    return resolve_owner_key(db,response,session_token=session,visitor_id=visitor)[0]

@router.get("/alarmlar", response_class=HTMLResponse)
def alerts_page(request:Request,response:Response,status:str|None=Query(None),firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id)
    return templates.TemplateResponse(request=request,name="advanced_alert_center.html",context={"alerts":list_alerts(owner_key=key,status=status),"selected_status":status or "","alert_types":sorted(ALERT_TYPES),"page_title":"Gelişmiş Alarmlar | FırsatAI"})
@router.get("/api/alerts/v13")
def api_list(response:Response,status:str|None=Query(None),firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id); return {"version":"13.8.1","items":list_alerts(owner_key=key,status=status)}
@router.post("/api/alerts/v13",status_code=201)
def api_create(payload:AlertCreate,response:Response,firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id)
    try:return create_alert(owner_key=key,**payload.model_dump())
    except ValueError as exc:raise HTTPException(422,str(exc))
@router.put("/api/alerts/v13/{alert_id}")
def api_update(alert_id:int,payload:AlertUpdate,response:Response,firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id); result=update_alert(owner_key=key,alert_id=alert_id,**payload.model_dump())
    if not result:raise HTTPException(404,"Alarm bulunamadı")
    return result
@router.delete("/api/alerts/v13/{alert_id}")
def api_delete(alert_id:int,response:Response,firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id)
    if not delete_alert(owner_key=key,alert_id=alert_id):raise HTTPException(404,"Alarm bulunamadı")
    return {"success":True}
@router.post("/api/alerts/v13/{alert_id}/enable")
def api_enable(alert_id:int,response:Response,firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id); result=update_alert(owner_key=key,alert_id=alert_id,is_active=True)
    if not result:raise HTTPException(404,"Alarm bulunamadı")
    return result
@router.post("/api/alerts/v13/{alert_id}/disable")
def api_disable(alert_id:int,response:Response,firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id); result=update_alert(owner_key=key,alert_id=alert_id,is_active=False)
    if not result:raise HTTPException(404,"Alarm bulunamadı")
    return result
@router.post("/api/alerts/v13/{alert_id}/evaluate")
def api_evaluate(alert_id:int,payload:AlertEvaluate,response:Response,firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id); result=evaluate_alert(owner_key=key,alert_id=alert_id,signals=payload.signals)
    if not result:raise HTTPException(404,"Alarm bulunamadı")
    return result
@router.get("/api/alerts/v13/{alert_id}/events")
def api_events(alert_id:int,response:Response,firsat_session:str|None=Cookie(None),visitor_id:str|None=Cookie(None),db:Session=Depends(get_db)):
    key=owner(response,db,firsat_session,visitor_id); return {"items":events(owner_key=key,alert_id=alert_id)}
@router.get("/admin/alerts",response_class=HTMLResponse)
def admin_alerts(request:Request):
    return templates.TemplateResponse(request=request,name="advanced_alert_admin.html",context={"summary":admin_summary(),"page_title":"Alarm Yönetimi | FırsatAI"})
@router.get("/api/admin/alerts/v13")
def admin_api(): return admin_summary()
