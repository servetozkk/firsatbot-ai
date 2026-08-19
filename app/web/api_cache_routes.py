from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request

from app.middleware.api_cache import CACHEABLE_PREFIXES, TTL_RULES
from app.services.api_cache_service import CACHE_ENGINE_VERSION, PUBLIC_API_CACHE

router = APIRouter(tags=["API Cache v13.7.1"])


@router.get("/api/cache/v13")
def api_cache_stats() -> dict:
    return {
        **PUBLIC_API_CACHE.stats(),
        "enabled": os.getenv("API_CACHE_ENABLED", "1").strip().lower() not in {"0", "false", "off", "no"},
        "cacheable_prefixes": list(CACHEABLE_PREFIXES),
        "ttl_rules": [{"prefix": prefix, "ttl_seconds": ttl} for prefix, ttl in TTL_RULES],
        "read_only": True,
    }


@router.post("/api/cache/v13/clear")
def clear_api_cache(request: Request) -> dict:
    configured_key = os.getenv("CACHE_ADMIN_KEY", "").strip()
    supplied_key = request.headers.get("x-cache-admin-key", "").strip()
    host = request.client.host if request.client else ""
    local_request = host in {"127.0.0.1", "::1", "localhost", "testclient"}
    if configured_key:
        if supplied_key != configured_key:
            raise HTTPException(status_code=403, detail="Geçersiz cache yönetim anahtarı")
    elif not local_request:
        raise HTTPException(status_code=403, detail="Cache temizleme yalnızca yerel erişime açık")

    cleared = PUBLIC_API_CACHE.clear()
    return {
        "engine_version": CACHE_ENGINE_VERSION,
        "cleared_entries": cleared,
        "status": "CACHE_CLEARED",
    }
