from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.price_integrity_v219_service import audit_product_prices, get_price_integrity_status

router = APIRouter(prefix="/api/price-integrity/v219", tags=["V21.9 Price Integrity & Quarantine"])


@router.get("/products/{global_product_id}")
def status(global_product_id: int, db: Session = Depends(get_db)):
    return get_price_integrity_status(db=db, global_product_id=global_product_id)


@router.post("/products/{global_product_id}/audit")
def audit(global_product_id: int, db: Session = Depends(get_db)):
    result = audit_product_prices(db=db, global_product_id=global_product_id)
    db.commit()
    return result


@router.get("/runtime")
def runtime_alias():
    return {
        "ok": True,
        "runtime_version": "21.9.0",
        "price_integrity_quarantine_engine": "enabled",
    }
