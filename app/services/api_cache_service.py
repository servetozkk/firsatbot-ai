from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

CACHE_ENGINE_VERSION = "13.7.1"


@dataclass(frozen=True)
class CacheRecord:
    status: int
    headers: tuple[tuple[bytes, bytes], ...]
    body: bytes
    etag: str
    created_at: float
    expires_at: float


class InMemoryApiCache:
    """Thread-safe, bounded TTL cache for public API responses."""

    def __init__(self, max_entries: int = 512) -> None:
        self.max_entries = max(16, int(max_entries))
        self._items: OrderedDict[str, CacheRecord] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._stores = 0
        self._evictions = 0
        self._invalidations = 0

    @staticmethod
    def make_etag(body: bytes) -> str:
        digest = hashlib.sha256(body).hexdigest()[:24]
        return f'"{digest}"'

    def get(self, key: str, now: float | None = None) -> CacheRecord | None:
        current = time.time() if now is None else now
        with self._lock:
            item = self._items.get(key)
            if item is None:
                self._misses += 1
                return None
            if item.expires_at <= current:
                self._items.pop(key, None)
                self._misses += 1
                return None
            self._items.move_to_end(key)
            self._hits += 1
            return item

    def put(
        self,
        key: str,
        *,
        status: int,
        headers: list[tuple[bytes, bytes]],
        body: bytes,
        ttl_seconds: int,
        now: float | None = None,
    ) -> CacheRecord:
        current = time.time() if now is None else now
        ttl = max(1, int(ttl_seconds))
        item = CacheRecord(
            status=status,
            headers=tuple(headers),
            body=body,
            etag=self.make_etag(body),
            created_at=current,
            expires_at=current + ttl,
        )
        with self._lock:
            self._items[key] = item
            self._items.move_to_end(key)
            self._stores += 1
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)
                self._evictions += 1
        return item

    def clear(self) -> int:
        with self._lock:
            count = len(self._items)
            self._items.clear()
            self._invalidations += 1
            return count

    def prune(self, now: float | None = None) -> int:
        current = time.time() if now is None else now
        with self._lock:
            expired = [key for key, value in self._items.items() if value.expires_at <= current]
            for key in expired:
                self._items.pop(key, None)
            return len(expired)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            requests = self._hits + self._misses
            return {
                "engine_version": CACHE_ENGINE_VERSION,
                "backend": "memory",
                "entries": len(self._items),
                "max_entries": self.max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "stores": self._stores,
                "evictions": self._evictions,
                "invalidations": self._invalidations,
                "hit_rate": round((self._hits / requests) * 100, 2) if requests else 0.0,
            }


PUBLIC_API_CACHE = InMemoryApiCache(max_entries=512)


def stable_cache_key(path: str, query_string: bytes) -> str:
    query = query_string.decode("latin-1") if query_string else ""
    return f"GET:{path}?{query}"


def json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
