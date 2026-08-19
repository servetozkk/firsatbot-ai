from pathlib import Path
from fastapi import APIRouter,HTTPException,Query,Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database.database import SessionLocal
from app.services.brand_center_service import list_brand_summaries,resolve_brand,brand_detail
from app.services.breadcrumb_service import page_breadcrumbs
router=APIRouter(tags=['Marka Merkezleri'])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent/'templates'))
@router.get('/markalar',response_class=HTMLResponse)
def brands_index(request:Request):
 db=SessionLocal()
 try:return templates.TemplateResponse(request=request,name='brand_centers.html',context={'brands':list_brand_summaries(db),'page_title':'Marka Merkezleri','breadcrumbs_v13':page_breadcrumbs(('Markalar',None))})
 finally:db.close()
@router.get('/marka-merkezi/{brand_slug}',response_class=HTMLResponse)
def brand_center(request:Request,brand_slug:str,sort:str=Query('price_asc')):
 db=SessionLocal()
 try:
  brand=resolve_brand(db,brand_slug)
  if not brand:raise HTTPException(404,'Marka bulunamadı')
  data=brand_detail(db,brand,sort=sort); data['breadcrumbs_v13']=page_breadcrumbs(('Markalar','/markalar'),(brand,None)); return templates.TemplateResponse(request=request,name='brand_center_detail.html',context=data)
 finally:db.close()
@router.get('/api/brand-centers/v13')
def brands_api():
 db=SessionLocal()
 try:return {'engine_version':'13.4.3','read_only':True,'brands':list_brand_summaries(db)}
 finally:db.close()
@router.get('/api/brand-centers/v13/{brand_slug}')
def brand_api(brand_slug:str,sort:str=Query('price_asc')):
 db=SessionLocal()
 try:
  brand=resolve_brand(db,brand_slug)
  if not brand:raise HTTPException(404,'Marka bulunamadı')
  return {'engine_version':'13.4.3','read_only':True,**brand_detail(db,brand,sort=sort)}
 finally:db.close()
