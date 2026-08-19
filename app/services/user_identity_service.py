from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from fastapi import Response
from sqlalchemy.orm import Session

from app.database.models import UserAccount, UserSession

SESSION_COOKIE = "firsat_session"
VISITOR_COOKIE = "visitor_id"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticated_user(db: Session, session_token: str | None) -> UserAccount | None:
    if not session_token:
        return None
    session = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == _token_hash(session_token),
            UserSession.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if session is None:
        return None
    return (
        db.query(UserAccount)
        .filter(UserAccount.id == session.user_id, UserAccount.is_active.is_(True))
        .first()
    )


def resolve_owner_key(
    db: Session,
    response: Response,
    *,
    session_token: str | None,
    visitor_id: str | None,
) -> tuple[str, UserAccount | None]:
    """Return the stable owner key used by favorites and price alerts.

    Authenticated users always use ``user:<id>`` so their data is isolated and
    available across devices. Guests keep a long-lived anonymous visitor id.
    """
    user = authenticated_user(db, session_token)
    if user is not None:
        return f"user:{user.id}", user

    value = visitor_id or str(uuid.uuid4())
    response.set_cookie(
        VISITOR_COOKIE,
        value,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return value, None
