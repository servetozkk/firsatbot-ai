from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.core.config import settings
from app.services.notification_delivery_service import ensure_delivery_queue

from app.database.models import (
    Favorite,
    PriceAlert,
    GlobalPriceAlert,
    ProductGroup,
    ProductOffer,
    RecentlyViewed,
    Store,
    UserAccount,
    UserSession,
    UserNotification,
    UserNotificationPreference,
    ProductReview,
    ReviewVote,
)

router = APIRouter(tags=["account"])
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
SESSION_COOKIE = "firsat_session"


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _current_user(db: Session, token: str | None):
    if not token:
        return None
    session = db.query(UserSession).filter(UserSession.token_hash == _token_hash(token), UserSession.expires_at > datetime.utcnow()).first()
    if not session:
        return None
    return db.query(UserAccount).filter(UserAccount.id == session.user_id, UserAccount.is_active.is_(True)).first()


def _create_session(db: Session, user: UserAccount) -> str:
    token = secrets.token_urlsafe(40)
    db.add(UserSession(user_id=user.id, token_hash=_token_hash(token), expires_at=datetime.utcnow() + timedelta(days=30)))
    user.last_login_at = datetime.utcnow()
    db.commit()
    return token


def _migrate_guest_data(db: Session, old_visitor: str | None, user_id: int):
    if not old_visitor:
        return
    new_key = f"user:{user_id}"
    for model in (Favorite, PriceAlert):
        rows = db.query(model).filter(model.visitor_id == old_visitor).all()
        for row in rows:
            existing = db.query(model).filter(model.visitor_id == new_key, model.product_group_id == row.product_group_id).first()
            if existing:
                if model is PriceAlert:
                    existing.target_price = row.target_price
                    existing.is_active = row.is_active
                db.delete(row)
            else:
                row.visitor_id = new_key

    global_alerts = db.query(GlobalPriceAlert).filter(GlobalPriceAlert.visitor_id == old_visitor).all()
    for row in global_alerts:
        existing = (
            db.query(GlobalPriceAlert)
            .filter(
                GlobalPriceAlert.visitor_id == new_key,
                GlobalPriceAlert.global_product_id == row.global_product_id,
                GlobalPriceAlert.global_variant_id == row.global_variant_id,
            )
            .first()
        )
        if existing:
            existing.target_price = row.target_price
            existing.is_active = row.is_active
            db.delete(row)
        else:
            row.visitor_id = new_key
    db.commit()




def _offer_summary(db: Session, group: ProductGroup) -> dict:
    offers = (
        db.query(ProductOffer, Store)
        .join(Store, Store.id == ProductOffer.store_id)
        .filter(ProductOffer.group_id == group.id, ProductOffer.current_price > 0)
        .order_by(ProductOffer.current_price.asc())
        .all()
    )
    active = [
        (offer, store) for offer, store in offers
        if str(offer.availability or "").strip().lower()
        not in {"stokta yok", "out of stock", "unavailable"}
    ]
    visible = active or offers
    prices = [float(offer.current_price) for offer, _ in visible if offer.current_price]
    old_prices = [float(offer.old_price) for offer, _ in visible if offer.old_price]
    best_price = min(prices) if prices else None
    reference_old_price = max(old_prices) if old_prices else None
    discount_percent = None
    if best_price and reference_old_price and reference_old_price > best_price:
        discount_percent = round((reference_old_price - best_price) / reference_old_price * 100)
    stores = []
    seen = set()
    for _, store in visible:
        if store.id in seen:
            continue
        seen.add(store.id)
        stores.append({
            "name": store.name,
            "code": store.code,
            "logo": f"/static/img/stores/{(store.code or 'generic').lower()}.svg",
        })
        if len(stores) >= 4:
            break
    return {
        "best_price": best_price,
        "discount_percent": discount_percent,
        "store_count": len({store.id for _, store in visible}),
        "stores": stores,
    }



def _create_notification(
    db: Session,
    *,
    user_id: int,
    event_key: str,
    kind: str,
    title: str,
    message: str,
    target_url: str | None = None,
) -> None:
    exists = (
        db.query(UserNotification)
        .filter(
            UserNotification.user_id == user_id,
            UserNotification.event_key == event_key,
        )
        .first()
    )
    if exists:
        return
    notification = UserNotification(
        user_id=user_id,
        event_key=event_key,
        kind=kind,
        title=title,
        message=message,
        target_url=target_url,
    )
    db.add(notification)
    db.flush()
    preferences = (
        db.query(UserNotificationPreference)
        .filter(UserNotificationPreference.user_id == user_id)
        .first()
    )
    if preferences is not None:
        ensure_delivery_queue(db, notification, preferences)


def _sync_user_notifications(db: Session, user: UserAccount) -> None:
    key = f"user:{user.id}"
    preferences = (
        db.query(UserNotificationPreference)
        .filter(UserNotificationPreference.user_id == user.id)
        .first()
    )
    if preferences is None:
        preferences = UserNotificationPreference(user_id=user.id)
        db.add(preferences)
        db.flush()

    if preferences.account_enabled:
        _create_notification(
        db,
        user_id=user.id,
        event_key="account:welcome",
        kind="welcome",
        title="Fırsat AI hesabın hazır",
        message="Favorilerini, fiyat alarmlarını ve son incelediğin ürünleri artık tek panelden yönetebilirsin.",
        target_url="/hesabim",
        )

    alerts = (
        db.query(PriceAlert, ProductGroup)
        .join(ProductGroup, ProductGroup.id == PriceAlert.product_group_id)
        .filter(PriceAlert.visitor_id == key, PriceAlert.is_active.is_(True))
        .all()
    )
    for alert, group in alerts:
        if not preferences.price_alert_enabled:
            break
        summary = _offer_summary(db, group)
        current = summary.get("best_price")
        if current and current <= float(alert.target_price):
            price_key = int(round(float(current) * 100))
            _create_notification(
                db,
                user_id=user.id,
                event_key=f"alert-reached:{alert.id}:{price_key}",
                kind="price_alert",
                title="Hedef fiyat gerçekleşti",
                message=(
                    f"{group.canonical_name} hedeflediğin "
                    f"{alert.target_price:,.2f} TL seviyesinin altına düştü. "
                    f"Güncel en düşük fiyat {current:,.2f} TL."
                ),
                target_url=f"/urun/{group.group_key}",
            )

    favorites = (
        db.query(Favorite, ProductGroup)
        .join(ProductGroup, ProductGroup.id == Favorite.product_group_id)
        .filter(Favorite.visitor_id == key)
        .all()
    )
    for favorite, group in favorites:
        if not preferences.favorite_drop_enabled:
            break
        summary = _offer_summary(db, group)
        discount = summary.get("discount_percent")
        current = summary.get("best_price")
        if current and discount and discount >= 5:
            price_key = int(round(float(current) * 100))
            _create_notification(
                db,
                user_id=user.id,
                event_key=f"favorite-discount:{group.id}:{price_key}",
                kind="favorite_drop",
                title="Favorindeki ürünün fiyatı düştü",
                message=(
                    f"{group.canonical_name} şu anda {current:,.2f} TL. "
                    f"Görünen fiyat avantajı yaklaşık %{discount}."
                ),
                target_url=f"/urun/{group.group_key}",
            )
    # Mevcut okunmamış bildirimler için yeni etkinleştirilen kanalları da kuyruğa al.
    queued_notifications = (
        db.query(UserNotification)
        .filter(UserNotification.user_id == user.id, UserNotification.is_read.is_(False))
        .all()
    )
    for queued_notification in queued_notifications:
        ensure_delivery_queue(db, queued_notification, preferences)
    db.commit()


def _set_auth_cookies(response: RedirectResponse, token: str, user_id: int):
    response.set_cookie(SESSION_COOKIE, token, max_age=60 * 60 * 24 * 30, httponly=True, samesite="lax")
    response.set_cookie("visitor_id", f"user:{user_id}", max_age=60 * 60 * 24 * 365, httponly=True, samesite="lax")


@router.get("/giris")
def login_page(request: Request, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        if _current_user(db, firsat_session):
            return RedirectResponse("/hesabim", status_code=303)
        return templates.TemplateResponse(request=request, name="account_login.html", context={"request": request, "mode": "login", "error": None})
    finally:
        db.close()


@router.post("/giris")
def login(request: Request, email: str = Form(...), password: str = Form(...), visitor_id: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = db.query(UserAccount).filter(UserAccount.email == email.strip().lower()).first()
        if not user or not _verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                request=request,
                name="account_login.html",
                context={"request": request, "mode": "login", "error": "E-posta veya şifre hatalı."},
                status_code=400,
            )
        _migrate_guest_data(db, visitor_id, user.id)
        token = _create_session(db, user)
        response = RedirectResponse("/hesabim", status_code=303)
        _set_auth_cookies(response, token, user.id)
        return response
    finally:
        db.close()


@router.get("/kayit")
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="account_login.html", context={"request": request, "mode": "register", "error": None})


@router.post("/kayit")
def register(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...), visitor_id: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        email = email.strip().lower()
        if len(password) < 8:
            return templates.TemplateResponse(
                request=request,
                name="account_login.html",
                context={"request": request, "mode": "register", "error": "Şifre en az 8 karakter olmalıdır."},
                status_code=400,
            )
        if db.query(UserAccount).filter(UserAccount.email == email).first():
            return templates.TemplateResponse(
                request=request,
                name="account_login.html",
                context={"request": request, "mode": "register", "error": "Bu e-posta zaten kayıtlı."},
                status_code=400,
            )
        user = UserAccount(email=email, display_name=name.strip()[:120], password_hash=_hash_password(password))
        db.add(user); db.commit(); db.refresh(user)
        _migrate_guest_data(db, visitor_id, user.id)
        token = _create_session(db, user)
        response = RedirectResponse("/hesabim", status_code=303)
        _set_auth_cookies(response, token, user.id)
        return response
    finally:
        db.close()


@router.get("/hesabim")
def account(request: Request, firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        user = _current_user(db, firsat_session)
        if not user:
            return RedirectResponse("/giris", status_code=303)
        _sync_user_notifications(db, user)
        unread_notifications = (
            db.query(UserNotification)
            .filter(UserNotification.user_id == user.id, UserNotification.is_read.is_(False))
            .count()
        )
        key = f"user:{user.id}"
        favorites = (db.query(Favorite, ProductGroup).join(ProductGroup, ProductGroup.id == Favorite.product_group_id)
                     .filter(Favorite.visitor_id == key).order_by(Favorite.created_at.desc()).all())
        alerts = (db.query(PriceAlert, ProductGroup).join(ProductGroup, ProductGroup.id == PriceAlert.product_group_id)
                  .filter(PriceAlert.visitor_id == key, PriceAlert.is_active.is_(True)).order_by(PriceAlert.updated_at.desc()).all())
        recent = (db.query(RecentlyViewed, ProductGroup).join(ProductGroup, ProductGroup.id == RecentlyViewed.product_group_id)
                  .filter(RecentlyViewed.user_id == user.id).order_by(RecentlyViewed.viewed_at.desc()).limit(8).all())

        favorite_cards = []
        for favorite, group in favorites:
            favorite_cards.append({"favorite": favorite, "group": group, **_offer_summary(db, group)})

        alert_cards = []
        for alert, group in alerts:
            summary = _offer_summary(db, group)
            alert_cards.append({
                "alert": alert,
                "group": group,
                "current_price": summary["best_price"],
                "reached": bool(summary["best_price"] and summary["best_price"] <= alert.target_price),
            })

        recent_cards = []
        for view, group in recent:
            summary = _offer_summary(db, group)
            recent_cards.append({"view": view, "group": group, "best_price": summary["best_price"]})

        # Kullanıcı analitiği: mevcut kalıcı verilerden güvenli ve hızlı özetler.
        now = datetime.utcnow()
        period_start = now - timedelta(days=30)

        category_counts: dict[str, int] = {}
        for _, group in recent:
            category = (group.category or "Diğer").strip() or "Diğer"
            category_counts[category] = category_counts.get(category, 0) + 1
        top_category = max(category_counts, key=category_counts.get) if category_counts else "Henüz veri yok"

        reached_alert_count = 0
        captured_advantage = 0.0
        for card in alert_cards:
            current = card.get("current_price")
            target = float(card["alert"].target_price or 0)
            if current and float(current) <= target:
                reached_alert_count += 1
                captured_advantage += max(target - float(current), 0)

        activity_counts = {(period_start.date() + timedelta(days=i)): 0 for i in range(31)}
        for favorite, _ in favorites:
            if favorite.created_at and favorite.created_at >= period_start:
                activity_counts[favorite.created_at.date()] = activity_counts.get(favorite.created_at.date(), 0) + 1
        for alert, _ in alerts:
            if alert.created_at and alert.created_at >= period_start:
                activity_counts[alert.created_at.date()] = activity_counts.get(alert.created_at.date(), 0) + 1
        recent_activity_rows = (
            db.query(RecentlyViewed)
            .filter(RecentlyViewed.user_id == user.id, RecentlyViewed.viewed_at >= period_start)
            .all()
        )
        for row in recent_activity_rows:
            activity_counts[row.viewed_at.date()] = activity_counts.get(row.viewed_at.date(), 0) + 1

        activity_series = [
            {
                "date": day.isoformat(),
                "label": day.strftime("%d.%m"),
                "value": activity_counts.get(day, 0),
            }
            for day in sorted(activity_counts)
        ]
        max_activity = max((item["value"] for item in activity_series), default=0) or 1
        for item in activity_series:
            item["height"] = max(8, round(item["value"] / max_activity * 100)) if item["value"] else 5

        analytics = {
            "tracked_products": len(favorites),
            "active_alerts": len(alerts),
            "reached_alerts": reached_alert_count,
            "captured_advantage": captured_advantage,
            "top_category": top_category,
            "monthly_activity": sum(item["value"] for item in activity_series),
            "activity_series": activity_series,
        }

        review_rows = (
            db.query(ProductReview, ProductGroup)
            .join(ProductGroup, ProductGroup.id == ProductReview.product_group_id)
            .filter(ProductReview.user_id == user.id)
            .order_by(ProductReview.updated_at.desc(), ProductReview.id.desc())
            .all()
        )
        review_cards = []
        total_helpful_votes = 0
        for review, group in review_rows:
            helpful_count = (
                db.query(ReviewVote)
                .filter(ReviewVote.review_id == review.id, ReviewVote.is_helpful.is_(True))
                .count()
            )
            total_helpful_votes += helpful_count
            review_cards.append({
                "review": review,
                "group": group,
                "helpful_count": helpful_count,
                **_offer_summary(db, group),
            })

        review_stats = {
            "count": len(review_rows),
            "average_rating": (sum(int(review.rating or 0) for review, _ in review_rows) / len(review_rows)) if review_rows else 0,
            "helpful_votes": total_helpful_votes,
            "approved_count": sum(1 for review, _ in review_rows if review.is_approved),
        }

        return templates.TemplateResponse(
            request=request,
            name="account_dashboard.html",
            context={
                "request": request,
                "user": user,
                "favorites": favorites,
                "favorite_cards": favorite_cards,
                "alerts": alerts,
                "alert_cards": alert_cards,
                "recent": recent,
                "recent_cards": recent_cards,
                "unread_notifications": unread_notifications,
                "analytics": analytics,
                "review_cards": review_cards,
                "review_stats": review_stats,
            },
        )
    finally:
        db.close()


@router.post("/cikis")
def logout(firsat_session: str | None = Cookie(default=None)):
    db = SessionLocal()
    try:
        if firsat_session:
            db.query(UserSession).filter(UserSession.token_hash == _token_hash(firsat_session)).delete()
            db.commit()
    finally:
        db.close()
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie("visitor_id")
    return response
