from pathlib import Path
from time import perf_counter
from fastapi import APIRouter,Request
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from app.database.database import SessionLocal
from app.services.global_catalog_search_service import build_global_search_candidates
from app.services.performance_cache_service import global_cache_stats,invalidate_global_catalog_cache
from app.services.v9_performance_service import apply_v99_sqlite_optimizations,database_performance_snapshot
router=APIRouter(prefix='/admin/v9-performance',tags=['V9 Performans'])
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent/'templates'))
@router.get('',response_class=HTMLResponse)
def page(request:Request,message:str|None=None):
    with SessionLocal() as db:
        s=perf_counter(); a=build_global_search_candidates(db=db,query=''); first=round((perf_counter()-s)*1000,2)
        s=perf_counter(); b=build_global_search_candidates(db=db,query=''); cached=round((perf_counter()-s)*1000,2)
    return templates.TemplateResponse(request=request,name='admin_v9_performance.html',context={'snapshot':database_performance_snapshot(),'cache':global_cache_stats(),'timings':{'first_search_ms':first,'cached_search_ms':cached,'candidate_count':len(b or a)},'message':message})
@router.post('/optimize')
def optimize():
    r=apply_v99_sqlite_optimizations(); invalidate_global_catalog_cache(); return RedirectResponse(f"/admin/v9-performance?message={len(r['indexes'])} indeks kontrol edildi",status_code=303)
@router.post('/clear-cache')
def clear():
    r=invalidate_global_catalog_cache(); return RedirectResponse(f"/admin/v9-performance?message=Cache temizlendi: {sum(r.values())}",status_code=303)
