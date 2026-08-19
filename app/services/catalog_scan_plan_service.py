from __future__ import annotations
import json, threading
from pathlib import Path
from typing import Any
from uuid import uuid4
from datetime import datetime
from app.category_scrapers.registry import CategoryScraperRegistry

PATH = Path("data/catalog_scan_plans.json")
LOCK = threading.RLock()

def _read():
    PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PATH.exists(): PATH.write_text("[]", encoding="utf-8")
    try: data=json.loads(PATH.read_text(encoding="utf-8") or "[]")
    except Exception: return []
    return data if isinstance(data,list) else []

def _write(items):
    tmp=PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(PATH)

def get_catalog_plans():
    with LOCK: items=_read()
    out=[]
    for x in items:
        if not isinstance(x,dict): continue
        sources=[{
            "store_code":str(s.get("store_code","")).strip().casefold(),
            "store_name":" ".join(str(s.get("store_name","")).split()),
            "url":str(s.get("url","")).strip(),
            "active":bool(s.get("active",True)),
        } for s in x.get("sources",[]) if isinstance(s,dict) and str(s.get("url","")).strip()]
        out.append({
            "id":str(x.get("id") or uuid4()),
            "name":" ".join(str(x.get("name","")).split()),
            "limit":max(1,min(int(x.get("limit",100) or 100),5000)),
            "interval_minutes":max(15,min(int(x.get("interval_minutes",60) or 60),1440)),
            "active":bool(x.get("active",True)),
            "sources":sources,
            "created_at":x.get("created_at"),
            "updated_at":x.get("updated_at"),
        })
    return out

def get_catalog_plan(plan_id):
    return next((x for x in get_catalog_plans() if x["id"]==str(plan_id)),None)

def get_active_catalog_plans():
    return [x for x in get_catalog_plans() if x["active"]]

def create_catalog_plan(name,limit,interval_minutes,active,source_urls):
    name=" ".join(str(name or "").split())
    if not name:return False,"Katalog adı boş bırakılamaz.",None
    reg=CategoryScraperRegistry(); stores={x["code"]:x for x in reg.list_stores()}
    sources=[]; errors=[]
    for code,url in source_urls.items():
        url=str(url or "").strip()
        if not url: continue
        try: detected=reg.detect_store_code(url)
        except Exception as e: errors.append(f"{code}: {e}"); continue
        if detected!=code: errors.append(f"{stores.get(code,{}).get('name',code)} alanına farklı mağaza bağlantısı girildi."); continue
        sources.append({"store_code":code,"store_name":stores[code]["name"],"url":url,"active":True})
    if errors:return False," ".join(errors),None
    if not sources:return False,"En az bir mağaza kategori bağlantısı girilmelidir.",None
    now=datetime.now().astimezone().isoformat(timespec="seconds")
    plan={"id":str(uuid4()),"name":name,"limit":max(1,min(int(limit),5000)),
          "interval_minutes":max(15,min(int(interval_minutes),1440)),
          "active":bool(active),"sources":sources,"created_at":now,"updated_at":now}
    with LOCK:
        items=_read()
        if any(str(x.get("name","")).casefold()==name.casefold() for x in items):
            return False,"Bu katalog adı zaten kayıtlı.",None
        items.append(plan);_write(items)
    return True,"Katalog tarama planı oluşturuldu.",plan

def set_catalog_plan_active(plan_id,active):
    with LOCK:
        items=_read();found=False
        for x in items:
            if str(x.get("id"))==str(plan_id):x["active"]=bool(active);found=True
        if not found:return False,"Katalog planı bulunamadı."
        _write(items)
    return True,"Katalog planı güncellendi."

def delete_catalog_plan(plan_id):
    with LOCK:
        items=_read();new=[x for x in items if str(x.get("id"))!=str(plan_id)]
        if len(new)==len(items):return False,"Katalog planı bulunamadı."
        _write(new)
    return True,"Katalog planı silindi."
