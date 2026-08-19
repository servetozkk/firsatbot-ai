from __future__ import annotations

import hashlib
import hmac
import ipaddress
import secrets
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response

from app.core.config import settings
from app.services.operational_log_service import record_operation_event

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
_PUBLIC_ADMIN_PATHS = {"/admin/access", "/admin/access/logout"}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    candidate = forwarded or (request.client.host if request.client else "unknown")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return candidate[:80] or "unknown"


def _admin_cookie_value(token: str) -> str:
    secret = settings.admin_access_token or settings.secret_key
    digest = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
    return f"{token}.{digest}"


def verify_admin_cookie(value: str | None) -> bool:
    if not value or "." not in value:
        return False
    token, supplied = value.rsplit(".", 1)
    secret = settings.admin_access_token or settings.secret_key
    expected = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def issue_admin_cookie(response: Response) -> None:
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        settings.admin_cookie_name,
        _admin_cookie_value(token),
        max_age=settings.admin_session_minutes * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(settings.admin_cookie_name, path="/")


class AdminAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/admin") or path in _PUBLIC_ADMIN_PATHS:
            return await call_next(request)
        if not settings.admin_protection_enabled:
            return await call_next(request)
        if verify_admin_cookie(request.cookies.get(settings.admin_cookie_name)):
            return await call_next(request)
        record_operation_event(
            level="WARNING", source="security", event_type="admin_access_denied",
            message="Yetkisiz admin erişimi engellendi.",
            details={"path": path, "ip": _client_ip(request)},
        )
        if request.method in _SAFE_METHODS:
            return RedirectResponse(f"/admin/access?next={path}", status_code=303)
        return JSONResponse({"detail": "Admin yetkilendirmesi gerekli."}, status_code=403)


class SameOriginCSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in _SAFE_METHODS or not settings.csrf_enabled:
            return await call_next(request)
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        host = request.headers.get("host", "")
        source = origin or referer
        browser_form = request.url.path.startswith(("/admin", "/hesabim", "/bildirim"))
        if source:
            parsed = urlsplit(source)
            allowed = parsed.netloc.casefold() == host.casefold() or parsed.netloc.casefold() in settings.trusted_hosts
            if not allowed:
                record_operation_event(
                    level="WARNING", source="security", event_type="csrf_blocked",
                    message="Farklı kaynaklı değiştirme isteği engellendi.",
                    details={"path": request.url.path, "origin": source, "host": host},
                )
                return PlainTextResponse("Geçersiz istek kaynağı.", status_code=403)
        elif browser_form and settings.is_production:
            return PlainTextResponse("İstek kaynağı doğrulanamadı.", status_code=403)
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    _lock = threading.RLock()
    _requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled or request.url.path.startswith("/static/"):
            return await call_next(request)
        now = time.monotonic()
        limit = settings.admin_rate_limit_per_minute if request.url.path.startswith("/admin") else settings.rate_limit_per_minute
        key = f"{_client_ip(request)}:{'admin' if request.url.path.startswith('/admin') else 'public'}"
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= limit:
                record_operation_event(
                    level="WARNING", source="security", event_type="rate_limit_exceeded",
                    message="İstek hız sınırı aşıldı.",
                    details={"path": request.url.path, "ip": _client_ip(request), "limit": limit},
                )
                return JSONResponse({"detail": "Çok fazla istek gönderildi."}, status_code=429, headers={"Retry-After": "60"})
            bucket.append(now)
        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(limit))
        response.headers.setdefault("X-RateLimit-Remaining", str(max(0, limit - len(bucket))))
        return response
