from __future__ import annotations

import os
import time
from typing import Iterable

from app.services.api_cache_service import PUBLIC_API_CACHE, CacheRecord, stable_cache_key

CACHEABLE_PREFIXES: tuple[str, ...] = (
    "/api/category-centers/v13",
    "/api/brand-centers/v13",
    "/api/store-centers/v13",
    "/api/campaign-center/v13",
    "/api/coupon-center/v13",
    "/api/stock-center/v13",
    "/api/new-products/v13",
    "/api/landing-pages/v13",
    "/api/sitemap/v13",
    "/api/performance/v13",
    "/api/search/autocomplete-v13",
    "/api/search/intelligence",
)

TTL_RULES: tuple[tuple[str, int], ...] = (
    ("/api/search/", 60),
    ("/api/stock-center/", 90),
    ("/api/campaign-center/", 180),
    ("/api/coupon-center/", 180),
    ("/api/new-products/", 300),
    ("/api/performance/", 30),
    ("/api/sitemap/", 600),
    ("/api/", 300),
)

MAX_CACHE_BODY = 2 * 1024 * 1024


def _header_dict(headers: Iterable[tuple[bytes, bytes]]) -> dict[bytes, bytes]:
    return {k.lower(): v for k, v in headers}


def _replace_header(headers: list[tuple[bytes, bytes]], name: bytes, value: bytes) -> list[tuple[bytes, bytes]]:
    lowered = name.lower()
    output = [(k, v) for k, v in headers if k.lower() != lowered]
    output.append((name, value))
    return output


def ttl_for_path(path: str) -> int:
    for prefix, ttl in TTL_RULES:
        if path.startswith(prefix):
            return ttl
    return 120


def is_cacheable_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in CACHEABLE_PREFIXES)


class PublicApiCacheMiddleware:
    """Caches only allow-listed, anonymous GET API responses.

    The cache is intentionally process-local. It adds ETag/304 support and never
    caches responses containing Set-Cookie, private/no-store directives, errors,
    or non JSON/XML payloads.
    """

    def __init__(self, app, enabled: bool | None = None) -> None:
        self.app = app
        env_enabled = os.getenv("API_CACHE_ENABLED", "1").strip().lower() not in {"0", "false", "off", "no"}
        self.enabled = env_enabled if enabled is None else enabled

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        request_headers = _header_dict(scope.get("headers", []))
        if (
            method not in {"GET", "HEAD"}
            or not is_cacheable_path(path)
            or b"authorization" in request_headers
            or b"cookie" in request_headers
        ):
            await self.app(scope, receive, send)
            return

        key = stable_cache_key(path, scope.get("query_string", b""))
        cached = PUBLIC_API_CACHE.get(key)
        if cached is not None:
            await self._send_cached(cached, request_headers, method, send)
            return

        start_message: dict | None = None
        body_parts: list[bytes] = []
        passthrough = False

        async def capture_send(message: dict) -> None:
            nonlocal start_message, passthrough
            if message["type"] == "http.response.start":
                start_message = message
                return
            if message["type"] != "http.response.body":
                await send(message)
                return

            body_parts.append(message.get("body", b""))
            if message.get("more_body", False):
                # Streaming responses are never cached. Flush what we captured.
                if start_message is not None and not passthrough:
                    await send(start_message)
                    passthrough = True
                await send(message)
                return

            if passthrough:
                await send(message)
                return

            if start_message is None:
                await send(message)
                return

            body = b"".join(body_parts)
            status = int(start_message.get("status", 200))
            headers = list(start_message.get("headers", []))
            response_headers = _header_dict(headers)
            content_type = response_headers.get(b"content-type", b"").lower()
            cache_control = response_headers.get(b"cache-control", b"").lower()
            can_store = (
                status == 200
                and len(body) <= MAX_CACHE_BODY
                and (b"application/json" in content_type or b"application/xml" in content_type or b"text/xml" in content_type)
                and b"set-cookie" not in response_headers
                and b"no-store" not in cache_control
                and b"private" not in cache_control
            )

            if can_store:
                ttl = ttl_for_path(path)
                record = PUBLIC_API_CACHE.put(
                    key,
                    status=status,
                    headers=headers,
                    body=body,
                    ttl_seconds=ttl,
                )
                headers = _replace_header(headers, b"etag", record.etag.encode("ascii"))
                headers = _replace_header(headers, b"cache-control", f"public, max-age={ttl}".encode("ascii"))
                headers = _replace_header(headers, b"x-firsatai-cache", b"MISS")
                headers = _replace_header(headers, b"vary", b"Accept-Encoding")
                start_message = {**start_message, "headers": headers}

            await send(start_message)
            await send({"type": "http.response.body", "body": b"" if method == "HEAD" else body, "more_body": False})

        await self.app(scope, receive, capture_send)

    async def _send_cached(self, cached: CacheRecord, request_headers: dict[bytes, bytes], method: str, send) -> None:
        if request_headers.get(b"if-none-match") == cached.etag.encode("ascii"):
            await send({
                "type": "http.response.start",
                "status": 304,
                "headers": [(b"etag", cached.etag.encode("ascii")), (b"x-firsatai-cache", b"HIT")],
            })
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        age = max(0, int(time.time() - cached.created_at))
        remaining = max(0, int(cached.expires_at - time.time()))
        headers = list(cached.headers)
        headers = _replace_header(headers, b"etag", cached.etag.encode("ascii"))
        headers = _replace_header(headers, b"cache-control", f"public, max-age={remaining}".encode("ascii"))
        headers = _replace_header(headers, b"age", str(age).encode("ascii"))
        headers = _replace_header(headers, b"x-firsatai-cache", b"HIT")
        headers = _replace_header(headers, b"vary", b"Accept-Encoding")
        await send({"type": "http.response.start", "status": cached.status, "headers": headers})
        await send({"type": "http.response.body", "body": b"" if method == "HEAD" else cached.body, "more_body": False})
