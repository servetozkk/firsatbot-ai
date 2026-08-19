from __future__ import annotations

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Yanıt süresini ölçer ve yavaş istekleri terminalde bildirir."""

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.1f}"
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
        if elapsed_ms >= settings.slow_request_ms:
            print(
                f"Yavaş istek: {request.method} {request.url.path} "
                f"{elapsed_ms:.0f} ms"
            )
        return response
