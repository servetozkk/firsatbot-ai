from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database.database import SessionLocal
from app.services.campaign_center_service import ENGINE_VERSION, list_campaigns

from app.services.breadcrumb_service import page_breadcrumbs
router=APIRouter(tags=["Kampanya Merkezi v13.5.0"])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent/"templates"))

@router.get("/kampanyalar",response_class=HTMLResponse)
def campaign_center(request:Request,type:str|None=None,store:str|None=None,category:str|None=None):
    db=SessionLocal()
    try:
        data=list_campaigns(db,type,store,category)
        return templates.TemplateResponse(request=request,name="campaign_center.html",context={"campaigns":data,"engine_version":ENGINE_VERSION,
            "seo_title":"Kampanyalar ve Fiyat Düşüşleri | FırsatAI","seo_description":"Mağaza kampanyalarını, fiyat düşüşlerini, ücretsiz kargo ve taksit avantajlarını karşılaştırın.",
            "canonical_url":str(request.base_url).rstrip("/")+"/kampanyalar","breadcrumbs":[("Ana Sayfa","/"),("Kampanyalar",None)],"breadcrumbs_v13":page_breadcrumbs(("Kampanyalar",None))})
    finally: db.close()

@router.get("/api/campaign-center/v13")
def campaign_api(type:str|None=None,store:str|None=None,category:str|None=None,limit:int=100):
    db=SessionLocal()
    try:return list_campaigns(db,type,store,category,min(max(limit,1),250))
    finally:db.close()
