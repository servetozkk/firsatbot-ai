from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.database.models import NotificationDelivery, UserNotification
from app.web.account_routes import SESSION_COOKIE, _current_user, _sync_user_notifications
from app.services.notification_delivery_service import process_email_queue, smtp_configured

router = APIRouter(tags=["notifications"])
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@router.get("/bildirimler")
def notification_center(request: Request, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        _sync_user_notifications(db, user)
        notifications = (
            db.query(UserNotification)
            .filter(UserNotification.user_id == user.id)
            .order_by(UserNotification.is_read.asc(), UserNotification.created_at.desc())
            .limit(100)
            .all()
        )
        unread_count = sum(1 for item in notifications if not item.is_read)
        return templates.TemplateResponse(
            request=request,
            name="notification_center.html",
            context={
                "request": request,
                "user": user,
                "notifications": notifications,
                "unread_count": unread_count,
            },
        )
    finally:
        db.close()


@router.post("/bildirimler/{notification_id}/okundu")
def mark_notification_read(notification_id: int, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        item = (
            db.query(UserNotification)
            .filter(UserNotification.id == notification_id, UserNotification.user_id == user.id)
            .first()
        )
        if item:
            item.is_read = True
            item.read_at = datetime.utcnow()
            db.commit()
            return RedirectResponse(item.target_url or "/bildirimler", status_code=303)
        return RedirectResponse("/bildirimler", status_code=303)
    finally:
        db.close()


@router.post("/bildirimler/tumunu-okundu")
def mark_all_read(firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        now = datetime.utcnow()
        items = (
            db.query(UserNotification)
            .filter(UserNotification.user_id == user.id, UserNotification.is_read.is_(False))
            .all()
        )
        for item in items:
            item.is_read = True
            item.read_at = now
        db.commit()
        return RedirectResponse("/bildirimler", status_code=303)
    finally:
        db.close()


@router.post("/bildirimler/{notification_id}/sil")
def delete_notification(notification_id: int, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        item = (
            db.query(UserNotification)
            .filter(UserNotification.id == notification_id, UserNotification.user_id == user.id)
            .first()
        )
        if item:
            db.delete(item)
            db.commit()
        return RedirectResponse("/bildirimler", status_code=303)
    finally:
        db.close()

@router.get("/bildirim-ayarlari")
def notification_settings(request: Request, firsat_session: str | None = Cookie(default=None)):
    from app.database.models import NotificationDelivery, UserNotificationPreference
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        preferences = (
            db.query(UserNotificationPreference)
            .filter(UserNotificationPreference.user_id == user.id)
            .first()
        )
        if preferences is None:
            preferences = UserNotificationPreference(user_id=user.id)
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
        saved = request.query_params.get("saved") == "1"
        return templates.TemplateResponse(
            request=request,
            name="notification_settings.html",
            context={"request": request, "user": user, "preferences": preferences, "saved": saved, "queue_processed": request.query_params.get("queue") == "1", "smtp_ready": smtp_configured()},
        )
    finally:
        db.close()


@router.post("/bildirim-ayarlari")
def save_notification_settings(
    price_alert_enabled: str | None = Form(default=None),
    favorite_drop_enabled: str | None = Form(default=None),
    account_enabled: str | None = Form(default=None),
    browser_enabled: str | None = Form(default=None),
    email_enabled: str | None = Form(default=None),
    quiet_hours_enabled: str | None = Form(default=None),
    quiet_start: str = Form(default="22:00"),
    quiet_end: str = Form(default="08:00"),
    firsat_session: str | None = Cookie(default=None),
):
    from app.database.models import NotificationDelivery, UserNotificationPreference
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        preferences = (
            db.query(UserNotificationPreference)
            .filter(UserNotificationPreference.user_id == user.id)
            .first()
        )
        if preferences is None:
            preferences = UserNotificationPreference(user_id=user.id)
            db.add(preferences)
        preferences.price_alert_enabled = price_alert_enabled == "on"
        preferences.favorite_drop_enabled = favorite_drop_enabled == "on"
        preferences.account_enabled = account_enabled == "on"
        preferences.browser_enabled = browser_enabled == "on"
        preferences.email_enabled = email_enabled == "on"
        preferences.quiet_hours_enabled = quiet_hours_enabled == "on"
        preferences.quiet_start = quiet_start if len(quiet_start) == 5 else "22:00"
        preferences.quiet_end = quiet_end if len(quiet_end) == 5 else "08:00"
        db.flush()
        # Tercih açıldığında daha önce oluşmuş okunmamış bildirimleri de kuyruğa ekle.
        from app.services.notification_delivery_service import ensure_delivery_queue
        pending_notifications = db.query(UserNotification).filter(
            UserNotification.user_id == user.id,
            UserNotification.is_read.is_(False),
        ).all()
        for pending_notification in pending_notifications:
            ensure_delivery_queue(db, pending_notification, preferences)
        db.commit()
        return RedirectResponse("/bildirim-ayarlari?saved=1", status_code=303)
    finally:
        db.close()


@router.get("/api/bildirimler/tarayici-bekleyen")
def pending_browser_notifications(firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return JSONResponse({"items": [], "authenticated": False})
        _sync_user_notifications(db, user)
        now = datetime.now()
        rows = (
            db.query(NotificationDelivery, UserNotification)
            .join(UserNotification, UserNotification.id == NotificationDelivery.notification_id)
            .filter(
                NotificationDelivery.user_id == user.id,
                NotificationDelivery.channel == "browser",
                NotificationDelivery.status == "queued",
                NotificationDelivery.scheduled_at <= now,
            )
            .order_by(NotificationDelivery.created_at.asc())
            .limit(10)
            .all()
        )
        items = []
        for delivery, notification in rows:
            items.append({
                "delivery_id": delivery.id,
                "title": notification.title,
                "body": notification.message or "",
                "url": notification.target_url or "/bildirimler",
                "tag": notification.event_key,
            })
        return {"authenticated": True, "items": items}
    finally:
        db.close()


@router.post("/api/bildirimler/tarayici/{delivery_id}/teslim-edildi")
def browser_notification_delivered(delivery_id: int, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return JSONResponse({"success": False}, status_code=401)
        delivery = db.query(NotificationDelivery).filter(
            NotificationDelivery.id == delivery_id,
            NotificationDelivery.user_id == user.id,
            NotificationDelivery.channel == "browser",
        ).first()
        if not delivery:
            return JSONResponse({"success": False}, status_code=404)
        delivery.status = "sent"
        delivery.sent_at = datetime.utcnow()
        delivery.attempts += 1
        db.commit()
        return {"success": True}
    finally:
        db.close()


@router.post("/bildirimler/kuyrugu-isle")
def process_my_notification_queue(firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        process_email_queue(db, limit=25)
        return RedirectResponse("/bildirim-ayarlari?queue=1", status_code=303)
    finally:
        db.close()


@router.get("/bildirim-gonderimleri")
def notification_delivery_history(request: Request, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        deliveries = (
            db.query(NotificationDelivery, UserNotification)
            .join(UserNotification, UserNotification.id == NotificationDelivery.notification_id)
            .filter(NotificationDelivery.user_id == user.id)
            .order_by(NotificationDelivery.created_at.desc())
            .limit(100)
            .all()
        )
        return templates.TemplateResponse(
            request=request,
            name="notification_delivery_history.html",
            context={
                "request": request,
                "user": user,
                "deliveries": deliveries,
                "smtp_ready": smtp_configured(),
            },
        )
    finally:
        db.close()
