from __future__ import annotations

import asyncio
from pathlib import Path

from app.middleware.api_cache import PublicApiCacheMiddleware, is_cacheable_path, ttl_for_path
from app.services.api_cache_service import CACHE_ENGINE_VERSION, PUBLIC_API_CACHE, InMemoryApiCache

ROOT = Path(__file__).resolve().parents[2]


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


async def call_app(app, *, path="/api/category-centers/v13", headers=None):
    sent = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 1234),
        "server": ("127.0.0.1", 8000),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)
    return sent


async def origin_app(scope, receive, send):
    origin_app.calls += 1
    body = b'{"status":"ok","value":42}'
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
    })
    await send({"type": "http.response.body", "body": body, "more_body": False})


origin_app.calls = 0


def header_value(messages, name: bytes):
    start = next(m for m in messages if m["type"] == "http.response.start")
    headers = {k.lower(): v for k, v in start.get("headers", [])}
    return headers.get(name.lower())


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.7.1", "VERSION 13.7.1")
    ok(CACHE_ENGINE_VERSION == "13.7.1", "API cache motoru sürümü doğru")

    cache = InMemoryApiCache(max_entries=16)
    record = cache.put("k", status=200, headers=[], body=b"abc", ttl_seconds=10, now=100.0)
    ok(cache.get("k", now=101.0) is not None, "TTL cache geçerli kaydı döndürüyor")
    ok(cache.get("k", now=111.0) is None, "TTL süresi dolan kayıt temizleniyor")
    ok(record.etag.startswith('"') and record.etag.endswith('"'), "ETag güvenli biçimde üretiliyor")
    ok(is_cacheable_path("/api/category-centers/v13"), "halka açık API allow-list içinde")
    ok(not is_cacheable_path("/api/bildirimler/tarayici-bekleyen"), "kişisel API cache dışında")
    ok(ttl_for_path("/api/search/intelligence") == 60, "arama API kısa TTL kullanıyor")

    PUBLIC_API_CACHE.clear()
    origin_app.calls = 0
    middleware = PublicApiCacheMiddleware(origin_app, enabled=True)
    first = asyncio.run(call_app(middleware))
    second = asyncio.run(call_app(middleware))
    ok(origin_app.calls == 1, "ikinci aynı API isteği origin servise gitmiyor")
    ok(header_value(first, b"x-firsatai-cache") == b"MISS", "ilk API isteği cache MISS")
    ok(header_value(second, b"x-firsatai-cache") == b"HIT", "ikinci API isteği cache HIT")
    etag = header_value(second, b"etag")
    third = asyncio.run(call_app(middleware, headers=[(b"if-none-match", etag)]))
    third_start = next(m for m in third if m["type"] == "http.response.start")
    ok(third_start["status"] == 304, "ETag eşleşmesinde 304 Not Modified üretiliyor")

    main_text = (ROOT / "main.py").read_text(encoding="utf-8-sig")
    ok("PublicApiCacheMiddleware" in main_text, "API cache middleware uygulamaya bağlı")
    ok("api_cache_router" in main_text, "API cache yönetim router'ı uygulamaya bağlı")

    print("\nFırsatAI v13.7.1 API Cache smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
