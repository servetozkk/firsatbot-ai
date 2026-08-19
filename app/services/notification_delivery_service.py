from __future__ import annotations

import os
import smtplib
from datetime import datetime, time, timedelta
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.database.models import (
    NotificationDelivery,
    UserAccount,
    UserNotification,
    UserNotificationPreference,
)


def _parse_clock(value: str, fallback: time) -> time:
    try:
        hour, minute = value.split(":", 1)
        return time(int(hour), int(minute))
    except Exception:
        return fallback


def in_quiet_hours(preferences: UserNotificationPreference, now: datetime | None = None) -> bool:
    if not preferences.quiet_hours_enabled:
        return False
    now = now or datetime.now()
    current = now.time().replace(second=0, microsecond=0)
    start = _parse_clock(preferences.quiet_start, time(22, 0))
    end = _parse_clock(preferences.quiet_end, time(8, 0))
    if start == end:
        return True
    if start < end:
        return start <= current < end
    return current >= start or current < end


def next_allowed_time(preferences: UserNotificationPreference, now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    if not in_quiet_hours(preferences, now):
        return now
    end = _parse_clock(preferences.quiet_end, time(8, 0))
    candidate = now.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def ensure_delivery_queue(db: Session, notification: UserNotification, preferences: UserNotificationPreference) -> None:
    scheduled_at = next_allowed_time(preferences)
    channels: list[str] = []
    if preferences.browser_enabled:
        channels.append("browser")
    if preferences.email_enabled:
        channels.append("email")
    for channel in channels:
        exists = db.query(NotificationDelivery).filter(
            NotificationDelivery.notification_id == notification.id,
            NotificationDelivery.channel == channel,
        ).first()
        if not exists:
            db.add(NotificationDelivery(
                notification_id=notification.id,
                user_id=notification.user_id,
                channel=channel,
                scheduled_at=scheduled_at,
            ))


def _smtp_settings() -> dict[str, object]:
    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_email": os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USERNAME", "")).strip(),
        "from_name": os.getenv("SMTP_FROM_NAME", "Fırsat AI").strip(),
        "use_tls": os.getenv("SMTP_USE_TLS", "1").lower() not in {"0", "false", "no"},
    }


def smtp_configured() -> bool:
    cfg = _smtp_settings()
    return bool(cfg["host"] and cfg["from_email"])


def _send_email(user: UserAccount, notification: UserNotification) -> str | None:
    cfg = _smtp_settings()
    if not cfg["host"] or not cfg["from_email"]:
        raise RuntimeError("SMTP ayarları eksik. SMTP_HOST ve SMTP_FROM_EMAIL tanımlanmalı.")
    message = EmailMessage()
    message["Subject"] = notification.title
    message["From"] = f"{cfg['from_name']} <{cfg['from_email']}>"
    message["To"] = user.email
    target = notification.target_url or "/bildirimler"
    public_url = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    message.set_content(
        f"{notification.title}\n\n{notification.message or ''}\n\nDetay: {public_url}{target}\n\nFırsat AI"
    )
    with smtplib.SMTP(str(cfg["host"]), int(cfg["port"]), timeout=20) as server:
        if cfg["use_tls"]:
            server.starttls()
        if cfg["username"]:
            server.login(str(cfg["username"]), str(cfg["password"]))
        result = server.send_message(message)
    return None if not result else str(result)


def process_email_queue(db: Session, limit: int = 25) -> dict[str, int]:
    now = datetime.now()
    rows = db.query(NotificationDelivery).filter(
        NotificationDelivery.channel == "email",
        NotificationDelivery.status.in_(["queued", "retry"]),
        NotificationDelivery.scheduled_at <= now,
        NotificationDelivery.attempts < 5,
    ).order_by(NotificationDelivery.scheduled_at.asc()).limit(limit).all()
    stats = {"processed": 0, "sent": 0, "failed": 0}
    for delivery in rows:
        stats["processed"] += 1
        delivery.attempts += 1
        notification = db.query(UserNotification).filter(UserNotification.id == delivery.notification_id).first()
        user = db.query(UserAccount).filter(UserAccount.id == delivery.user_id).first()
        if not notification or not user:
            delivery.status = "failed"
            delivery.last_error = "Kullanıcı veya bildirim bulunamadı."
            stats["failed"] += 1
            continue
        try:
            delivery.provider_message_id = _send_email(user, notification)
            delivery.status = "sent"
            delivery.sent_at = datetime.utcnow()
            delivery.last_error = None
            stats["sent"] += 1
        except Exception as exc:
            delivery.status = "retry" if delivery.attempts < 5 else "failed"
            delivery.last_error = str(exc)[:1000]
            delivery.scheduled_at = now + timedelta(minutes=min(60, 5 * delivery.attempts))
            stats["failed"] += 1
    db.commit()
    return stats
