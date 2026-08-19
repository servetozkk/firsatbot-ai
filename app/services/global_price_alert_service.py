from __future__ import annotations

from datetime import datetime
from typing import Any

from app.database.models import (
    GlobalOffer,
    GlobalPriceAlert,
    GlobalProduct,
    UserAccount,
    UserNotification,
    UserNotificationPreference,
)
from app.services.notification_delivery_service import ensure_delivery_queue


def current_best_price(
    *,
    db,
    global_product_id: int,
    global_variant_id: int | None,
) -> tuple[float | None, GlobalOffer | None]:
    query = db.query(GlobalOffer).filter(
        GlobalOffer.global_product_id == global_product_id,
        GlobalOffer.is_active.is_(True),
        GlobalOffer.is_hidden.is_(False),
        GlobalOffer.lifecycle_status == "ACTIVE",
        GlobalOffer.current_price > 0,
    )
    if global_variant_id is None:
        query = query.filter(GlobalOffer.global_variant_id.is_(None))
    else:
        query = query.filter(
            GlobalOffer.global_variant_id == global_variant_id
        )

    offers = query.all()
    if not offers:
        return None, None

    winner = min(
        offers,
        key=lambda item: (
            float(item.current_price or 0)
            + float(item.shipping_price or 0),
            item.id,
        ),
    )
    return (
        float(winner.current_price or 0)
        + float(winner.shipping_price or 0),
        winner,
    )


def _user_id_from_visitor(visitor_id: str) -> int | None:
    if not str(visitor_id or "").startswith("user:"):
        return None
    try:
        return int(str(visitor_id).split(":", 1)[1])
    except (TypeError, ValueError):
        return None


def _create_notification(
    *,
    db,
    alert: GlobalPriceAlert,
    product: GlobalProduct,
    current_price: float,
) -> UserNotification | None:
    user_id = _user_id_from_visitor(alert.visitor_id)
    if user_id is None:
        return None

    user = db.get(UserAccount, user_id)
    if user is None or not user.is_active:
        return None

    price_key = int(round(current_price * 100))
    event_key = f"global-alert:{alert.id}:{price_key}"
    existing = (
        db.query(UserNotification)
        .filter(
            UserNotification.user_id == user_id,
            UserNotification.event_key == event_key,
        )
        .first()
    )
    if existing is not None:
        return existing

    notification = UserNotification(
        user_id=user_id,
        event_key=event_key,
        kind="price_alert",
        title="Hedef fiyat gerçekleşti",
        message=(
            f"{product.canonical_name} hedeflediğin "
            f"{alert.target_price:,.2f} TL seviyesinin altına düştü. "
            f"Güncel en düşük toplam fiyat {current_price:,.2f} TL."
        ),
        target_url=f"/urun/{product.identity_key}"
        + (
            f"?variant={alert.global_variant_id}"
            if alert.global_variant_id is not None
            else ""
        ),
    )
    db.add(notification)
    db.flush()

    preferences = (
        db.query(UserNotificationPreference)
        .filter(UserNotificationPreference.user_id == user_id)
        .first()
    )
    if preferences is not None and preferences.price_alert_enabled:
        ensure_delivery_queue(db, notification, preferences)
    return notification


def evaluate_global_price_alerts(
    *,
    db,
    global_product_id: int,
    global_variant_id: int | None,
    current_price: float | None = None,
) -> dict[str, Any]:
    if current_price is None:
        current_price, _offer = current_best_price(
            db=db,
            global_product_id=global_product_id,
            global_variant_id=global_variant_id,
        )
    if current_price is None or current_price <= 0:
        return {"checked": 0, "triggered": 0}

    query = db.query(GlobalPriceAlert).filter(
        GlobalPriceAlert.global_product_id == global_product_id,
        GlobalPriceAlert.is_active.is_(True),
        GlobalPriceAlert.target_price >= float(current_price),
    )
    if global_variant_id is None:
        query = query.filter(GlobalPriceAlert.global_variant_id.is_(None))
    else:
        query = query.filter(
            GlobalPriceAlert.global_variant_id == global_variant_id
        )

    alerts = query.all()
    product = db.get(GlobalProduct, global_product_id)
    triggered = 0
    now = datetime.utcnow()

    for alert in alerts:
        price_key = int(round(float(current_price) * 100))
        if (
            alert.last_trigger_price_key == price_key
            and alert.last_triggered_at is not None
        ):
            continue

        alert.last_trigger_price = float(current_price)
        alert.last_trigger_price_key = price_key
        alert.last_triggered_at = now
        alert.trigger_count = int(alert.trigger_count or 0) + 1
        alert.updated_at = now

        if product is not None:
            _create_notification(
                db=db,
                alert=alert,
                product=product,
                current_price=float(current_price),
            )
        triggered += 1

    db.flush()
    return {"checked": len(alerts), "triggered": triggered}
