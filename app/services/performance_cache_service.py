from __future__ import annotations
import copy, threading, time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable

@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: float

class TTLCache:
    def __init__(self, max_entries: int = 256):
        self.max_entries=max_entries; self._items=OrderedDict(); self._lock=threading.RLock(); self._hits=0; self._misses=0
    def get(self,key):
        now=time.monotonic()
        with self._lock:
            e=self._items.get(key)
            if e is None: self._misses+=1; return None
            if e.expires_at<=now: self._items.pop(key,None); self._misses+=1; return None
            self._items.move_to_end(key); self._hits+=1; return copy.deepcopy(e.value)
    def set(self,key,value,ttl_seconds=60):
        with self._lock:
            self._items[key]=CacheEntry(copy.deepcopy(value),time.monotonic()+max(1,int(ttl_seconds))); self._items.move_to_end(key)
            while len(self._items)>self.max_entries: self._items.popitem(last=False)
    def get_or_create(self,key,factory:Callable[[],Any],ttl_seconds=60):
        value=self.get(key)
        if value is not None: return value
        value=factory(); self.set(key,value,ttl_seconds); return copy.deepcopy(value)
    def invalidate(self):
        with self._lock:
            count=len(self._items); self._items.clear(); return count
    def stats(self):
        with self._lock:
            total=self._hits+self._misses
            return {'entries':len(self._items),'hits':self._hits,'misses':self._misses,'hit_rate':round(self._hits/total*100,2) if total else 0.0}

global_search_cache=TTLCache(256)

def invalidate_global_catalog_cache(): return {'search':global_search_cache.invalidate()}
def global_cache_stats(): return {'search':global_search_cache.stats()}
