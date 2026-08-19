from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.models import (
    GlobalPriceAlert,
    GlobalProduct,
    PriceAlert,
    ProductGroup,
)
from app.services.user_identity_service import resolve_owner_key
from app.services.global_price_alert_service import (
    current_best_price,
    evaluate_global_price_alerts,
)


router = APIRouter(prefix="/price-alerts", tags=["price-alerts"])


class PriceAlertPayload(BaseModel):
    target_price: float = Field(gt=0)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _global_product_for_group(
    db: Session,
    group_id: int,
) -> tuple[ProductGroup, GlobalProduct | None]:
    group = db.get(ProductGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Ürün grubu bulunamadı.")
    global_product = (
        db.query(GlobalProduct)
        .filter(GlobalProduct.identity_key == group.group_key)
        .first()
    )
    return group, global_product


@router.get("/{group_id}")
def get_price_alert(
    group_id: int,
    response: Response,
    variant: int | None = Query(default=None),
    visitor_id: str | None = Cookie(default=None),
    firsat_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    visitor, user = resolve_owner_key(db, response, session_token=firsat_session, visitor_id=visitor_id)
    _group, global_product = _global_product_for_group(db, group_id)

    if global_product is not None:
        query = db.query(GlobalPriceAlert).filter(
            GlobalPriceAlert.visitor_id == visitor,
            GlobalPriceAlert.global_product_id == global_product.id,
            GlobalPriceAlert.is_active.is_(True),
        )
        if variant is None:
            query = query.filter(GlobalPriceAlert.global_variant_id.is_(None))
        else:
            query = query.filter(GlobalPriceAlert.global_variant_id == variant)
        alert = query.first()
        if alert is None:
            return {
                "active": False,
                "target_price": None,
                "data_source": "global_catalog_v9",
                "variant": variant,
                "authenticated": user is not None,
            }
        return {
            "active": True,
            "id": alert.id,
            "global_product_id": alert.global_product_id,
            "global_variant_id": alert.global_variant_id,
            "target_price": alert.target_price,
            "last_trigger_price": alert.last_trigger_price,
            "updated_at": alert.updated_at.isoformat()
            if alert.updated_at
            else None,
            "data_source": "global_catalog_v9",
            "authenticated": user is not None,
        }

    alert = (
        db.query(PriceAlert)
        .filter(
            PriceAlert.visitor_id == visitor,
            PriceAlert.product_group_id == group_id,
            PriceAlert.is_active.is_(True),
        )
        .first()
    )
    if alert is None:
        return {"active": False, "target_price": None, "authenticated": user is not None}
    return {
        "active": True,
        "id": alert.id,
        "product_group_id": alert.product_group_id,
        "target_price": alert.target_price,
        "updated_at": alert.updated_at.isoformat()
        if alert.updated_at
        else None,
    }


@router.post("/{group_id}")
def save_price_alert(
    group_id: int,
    payload: PriceAlertPayload,
    response: Response,
    variant: int | None = Query(default=None),
    visitor_id: str | None = Cookie(default=None),
    firsat_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    visitor, user = resolve_owner_key(db, response, session_token=firsat_session, visitor_id=visitor_id)
    _group, global_product = _global_product_for_group(db, group_id)

    if global_product is not None:
        query = db.query(GlobalPriceAlert).filter(
            GlobalPriceAlert.visitor_id == visitor,
            GlobalPriceAlert.global_product_id == global_product.id,
        )
        if variant is None:
            query = query.filter(GlobalPriceAlert.global_variant_id.is_(None))
        else:
            query = query.filter(GlobalPriceAlert.global_variant_id == variant)
        alert = query.first()

        if alert is None:
            alert = GlobalPriceAlert(
                visitor_id=visitor,
                global_product_id=global_product.id,
                global_variant_id=variant,
                target_price=float(payload.target_price),
                is_active=True,
            )
            db.add(alert)
        else:
            alert.target_price = float(payload.target_price)
            alert.is_active = True
            alert.last_trigger_price = None
            alert.last_trigger_price_key = None
            alert.last_triggered_at = None

        db.flush()
        best_price, _offer = current_best_price(
            db=db,
            global_product_id=global_product.id,
            global_variant_id=variant,
        )
        evaluate_global_price_alerts(
            db=db,
            global_product_id=global_product.id,
            global_variant_id=variant,
            current_price=best_price,
        )
        db.commit()
        db.refresh(alert)
        return {
            "success": True,
            "active": True,
            "id": alert.id,
            "global_product_id": alert.global_product_id,
            "global_variant_id": alert.global_variant_id,
            "target_price": alert.target_price,
            "current_best_price": best_price,
            "data_source": "global_catalog_v9",
            "authenticated": user is not None,
        }

    alert = (
        db.query(PriceAlert)
        .filter(
            PriceAlert.visitor_id == visitor,
            PriceAlert.product_group_id == group_id,
        )
        .first()
    )
    if alert is None:
        alert = PriceAlert(
            visitor_id=visitor,
            product_group_id=group_id,
            target_price=float(payload.target_price),
            is_active=True,
        )
        db.add(alert)
    else:
        alert.target_price = float(payload.target_price)
        alert.is_active = True

    db.commit()
    db.refresh(alert)
    return {
        "success": True,
        "active": True,
        "id": alert.id,
        "product_group_id": alert.product_group_id,
        "target_price": alert.target_price,
        "authenticated": user is not None,
    }


@router.delete("/{group_id}")
def delete_price_alert(
    group_id: int,
    response: Response,
    variant: int | None = Query(default=None),
    visitor_id: str | None = Cookie(default=None),
    firsat_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    visitor, user = resolve_owner_key(db, response, session_token=firsat_session, visitor_id=visitor_id)
    _group, global_product = _global_product_for_group(db, group_id)

    if global_product is not None:
        query = db.query(GlobalPriceAlert).filter(
            GlobalPriceAlert.visitor_id == visitor,
            GlobalPriceAlert.global_product_id == global_product.id,
        )
        if variant is None:
            query = query.filter(GlobalPriceAlert.global_variant_id.is_(None))
        else:
            query = query.filter(GlobalPriceAlert.global_variant_id == variant)
        alert = query.first()
        if alert is not None:
            db.delete(alert)
            db.commit()
        return {
            "success": True,
            "active": False,
            "data_source": "global_catalog_v9",
            "authenticated": user is not None,
        }

    alert = (
        db.query(PriceAlert)
        .filter(
            PriceAlert.visitor_id == visitor,
            PriceAlert.product_group_id == group_id,
        )
        .first()
    )
    if alert is not None:
        db.delete(alert)
        db.commit()
    return {"success": True, "active": False, "authenticated": user is not None}
