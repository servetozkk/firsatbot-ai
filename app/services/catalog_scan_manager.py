from __future__ import annotations
import json, threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass,field,asdict
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from app.services.catalog_scan_plan_service import get_catalog_plan,get_active_catalog_plans
from app.services.category_discovery_service import CategoryDiscoveryService

HISTORY=Path("data/catalog_scan_history.json");HLOCK=threading.RLock()
def now(): return datetime.now().astimezone().isoformat(timespec="seconds")
@dataclass(slots=True)
class Task:
    id:str; plan_id:str|None; plan_name:str; status:str="queued";progress:int=0
    message:str="Tarama sıraya alındı.";started_at:str|None=None;finished_at:str|None=None
    result:dict|None=None;error:str|None=None;logs:list[str]=field(default_factory=list)
    def to_dict(self):return asdict(self)
class Manager:
    def __init__(self):
        self.tasks={};self.lock=threading.RLock();self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix="catalog")
    def set(self,id,**kw):
        with self.lock:
            for k,v in kw.items():setattr(self.tasks[id],k,v)
    def log(self,id,msg):
        with self.lock:self.tasks[id].logs=(self.tasks[id].logs+[msg])[-200:]
    def get_task(self,id):
        with self.lock:
            t=self.tasks.get(str(id));return t.to_dict() if t else None
    def history(self,limit=20):
        if not HISTORY.exists():return []
        try:d=json.loads(HISTORY.read_text(encoding="utf-8"))
        except Exception:return []
        return list(reversed(d[-limit:])) if isinstance(d,list) else []
    def append(self,t):
        HISTORY.parent.mkdir(parents=True,exist_ok=True)
        with HLOCK:
            try:d=json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
            except Exception:d=[]
            if not isinstance(d,list):d=[]
            d.append(t);HISTORY.write_text(json.dumps(d[-200:],ensure_ascii=False,indent=2),encoding="utf-8")
    def start_plan(self,id):
        p=get_catalog_plan(id)
        if not p:raise ValueError("Katalog planı bulunamadı.")
        t=Task(str(uuid4()),p["id"],p["name"])
        with self.lock:self.tasks[t.id]=t
        self.pool.submit(self.run_plan,t.id,p);return t.to_dict()
    def start_all(self):
        plans=get_active_catalog_plans()
        if not plans:raise ValueError("Aktif katalog tarama planı bulunamadı.")
        t=Task(str(uuid4()),None,"Tüm aktif kataloglar")
        with self.lock:self.tasks[t.id]=t
        self.pool.submit(self.run_all,t.id,plans);return t.to_dict()
    def scan(self,id,p):
        sources=[s for s in p["sources"] if s.get("active",True)];svc=CategoryDiscoveryService();rows=[]
        for i,s in enumerate(sources,1):
            self.set(id,progress=max(3,int((i-1)/max(len(sources),1)*100)),message=f"{p['name']}: {s['store_name']} taranıyor ({i}/{len(sources)})")
            self.log(id,f"[{i}/{len(sources)}] {s['store_name']}")
            try:
                def on_progress(stage:str,fraction:float,detail:str,source_index:int=i,source=s):
                    fraction=max(0.0,min(1.0,float(fraction)))
                    if stage=="category": local=0.05+0.10*fraction
                    elif stage=="detail": local=0.15+0.25*fraction
                    elif stage=="reconciliation": local=0.40+0.58*fraction
                    else: local=0.02
                    overall=int((((source_index-1)+local)/max(len(sources),1))*100)
                    overall=max(1,min(99,overall))
                    phase={"category":"bağlantılar","detail":"ürün detayları","reconciliation":"mağazalar arası eşleştirme"}.get(stage,stage)
                    self.set(id,progress=overall,message=f"{p['name']}: {source['store_name']} — {phase}: {detail}")
                r=svc.scan_and_save(
                    category_url=s["url"],
                    limit=p["limit"],
                    reconciliation_product_limit=5,
                    progress_callback=on_progress,
                ).to_dict()
                self.set(id,progress=min(99,int(i/max(len(sources),1)*100)),message=f"{p['name']}: {s['store_name']} tamamlandı ({i}/{len(sources)})")
                rows.append({"store_name":s["store_name"],"success":bool(r.get("success")),"result":r})
                self.log(id,f"✓ {s['store_name']}: {r.get('found_count',0)} bulundu, {r.get('saved_count',0)} işlendi")
            except Exception as e:
                rows.append({"store_name":s["store_name"],"success":False,"error":f"{type(e).__name__}: {e}"})
                self.log(id,f"✗ {s['store_name']}: {type(e).__name__}: {e}")
        return {"plan_name":p["name"],"store_count":len(sources),
          "failed_store_count":sum(not x["success"] for x in rows),
          "found_count":sum(int(x.get("result",{}).get("found_count",0)) for x in rows),
          "saved_count":sum(int(x.get("result",{}).get("saved_count",0)) for x in rows),"results":rows}
    def run_plan(self,id,p):
        self.set(id,status="running",progress=1,started_at=now(),message=f"{p['name']} taranıyor")
        try:
            r=self.scan(id,p);failed=r["failed_store_count"]
            self.set(id,status="completed" if not failed else "completed_with_errors",progress=100,finished_at=now(),result=r,
                     error=None if not failed else f"{failed} mağazada hata oluştu.",
                     message=f"{r['store_count']} mağaza tarandı; {r['found_count']} ürün bulundu, {r['saved_count']} kayıt işlendi.")
        except Exception as e:self.set(id,status="failed",progress=100,finished_at=now(),error=str(e),message="Tarama başarısız.")
        self.append(self.get_task(id) or {})
    def run_all(self,id,plans):
        self.set(id,status="running",progress=1,started_at=now(),message=f"{len(plans)} katalog taranacak")
        out=[]
        for i,p in enumerate(plans,1):
            self.set(id,progress=int((i-1)/len(plans)*100),message=f"{p['name']} ({i}/{len(plans)})")
            out.append(self.scan(id,p))
        failed=sum(x["failed_store_count"] for x in out)
        self.set(id,status="completed" if not failed else "completed_with_errors",progress=100,finished_at=now(),
                 result={"catalog_count":len(plans),"results":out},
                 message=f"{len(plans)} katalog tarandı.",error=None if not failed else f"{failed} mağaza hata verdi.")
        self.append(self.get_task(id) or {})
catalog_scan_manager=Manager()
