from __future__ import annotations
from threading import RLock
from time import time
import re
from typing import Any
from app.services.store_retry_intelligence_v2360 import store_retry_intelligence_v2360

_lock=RLock()
_state: dict[tuple[str,str],dict[str,Any]]={}

def retry_context_key_v2361(search_query:str, source_name:str="")->str:
    text=f"{search_query or ''} {source_name or ''}".casefold()
    return re.sub(r"\s+"," ",text).strip()[:500]

def _key(store_code:str, context_key:str, failure_class:str|None)->tuple[str,str]:
    store=str(store_code or "").casefold()
    return (store,"*") if str(failure_class or "").upper()=="SECURITY_CHALLENGE" else (store,context_key)

def record_store_attempt_v2361(*,store_code:str,context_key:str,success:bool,failure_class:str|None)->dict[str,Any]:
    intel=store_retry_intelligence_v2360(success=bool(success),failure_class=failure_class)
    store=str(store_code or "").casefold()
    with _lock:
        if success:
            _state.pop((store,"*"),None); _state.pop((store,context_key),None)
            return intel
        mode=str(intel.get("retry_mode") or "NONE").upper()
        retry_after=intel.get("retry_after_seconds")
        now=time()
        _state[_key(store,context_key,failure_class)]={
            "store_code":store,"context_key":context_key,"failure_class":failure_class,
            "reliability_score":intel.get("reliability_score"),"retryable":bool(intel.get("retryable")),
            "retry_mode":mode,"retry_after_seconds":retry_after,
            "next_retry_at":(now+float(retry_after) if retry_after is not None and mode in {"DEFERRED","TRANSIENT"} else None),
            "recommended_action":intel.get("recommended_action"),"reason":intel.get("reason"),"recorded_at":now,
        }
    return intel

def scheduler_decision_v2361(*,store_code:str,context_key:str)->dict[str,Any]:
    store=str(store_code or "").casefold(); now=time()
    with _lock:
        row=_state.get((store,"*")); scope="STORE_GLOBAL"
        if row is None:
            row=_state.get((store,context_key)); scope="PRODUCT_CONTEXT"
        if row is None:
            return {"allow":True,"scheduler_skipped":False,"reason":"no-retry-state"}
        mode=str(row.get("retry_mode") or "NONE").upper()
        if mode=="CONTEXT_CHANGE_ONLY":
            return {"allow":False,"scheduler_skipped":True,"state_scope":scope,
                    "reliability_score":row.get("reliability_score"),"retry_mode":mode,
                    "retry_after_remaining_seconds":None,"recommended_action":row.get("recommended_action"),
                    "reason":row.get("reason")}
        nxt=row.get("next_retry_at")
        if nxt is not None and now<float(nxt):
            return {"allow":False,"scheduler_skipped":True,"state_scope":scope,
                    "reliability_score":row.get("reliability_score"),"retry_mode":mode,
                    "retry_after_remaining_seconds":max(1,int(round(float(nxt)-now))),
                    "recommended_action":row.get("recommended_action"),"reason":row.get("reason")}
        return {"allow":True,"scheduler_skipped":False,"state_scope":scope,
                "reliability_score":row.get("reliability_score"),"retry_mode":mode,
                "retry_after_remaining_seconds":0,"recommended_action":row.get("recommended_action"),
                "reason":"cooldown-expired"}

def retry_scheduler_snapshot_v2361()->list[dict[str,Any]]:
    now=time()
    with _lock:
        out=[]
        for row in _state.values():
            item=dict(row); nxt=item.get("next_retry_at")
            item["retry_after_remaining_seconds"]=(max(0,int(round(float(nxt)-now))) if nxt is not None else None)
            out.append(item)
        return out

def clear_retry_scheduler_state_v2361()->None:
    with _lock: _state.clear()
