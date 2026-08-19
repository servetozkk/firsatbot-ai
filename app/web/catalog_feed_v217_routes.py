from fastapi import APIRouter, Query
from app.services.smart_catalog_refresh_v217_service import get_smart_refresh_status, smart_refresh_product

router = APIRouter(prefix='/api/catalog-feed/v217', tags=['V21.7 Smart Catalog Refresh'])

@router.get('/status')
def status(global_product_id: int | None = Query(default=None, ge=1)):
    return {'engine': 'FIRSATAI_SMART_CATALOG_REFRESH', 'engine_version': '21.7.0', **get_smart_refresh_status(global_product_id)}

@router.post('/products/{global_product_id}/refresh')
def refresh(global_product_id: int, candidate_limit: int = Query(50, ge=5, le=100), parallel_workers: int = Query(3, ge=1, le=6), force: bool = Query(False)):
    return smart_refresh_product(global_product_id=global_product_id, candidate_limit=candidate_limit, parallel_workers=parallel_workers, force=force)
