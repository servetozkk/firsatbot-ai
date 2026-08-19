from pathlib import Path
ROOT=Path.cwd()
def main():
 p=ROOT/'app/database/database.py'; t=p.read_text(encoding='utf-8')
 if 'PRAGMA cache_size=-32768' not in t: t=t.replace('        cursor.execute("PRAGMA temp_store=MEMORY")','        cursor.execute("PRAGMA temp_store=MEMORY")\n        cursor.execute("PRAGMA cache_size=-32768")\n        cursor.execute("PRAGMA mmap_size=268435456")\n        cursor.execute("PRAGMA wal_autocheckpoint=1000")',1); p.write_text(t,encoding='utf-8')
 p=ROOT/'app/services/catalog_reconciliation_service.py'; t=p.read_text(encoding='utf-8'); imp='from app.services.performance_cache_service import invalidate_global_catalog_cache\n'; anchor='from app.services.product_identity_service import ProductIdentityService\n'
 if imp not in t: t=t.replace(anchor,anchor+imp,1)
 if 'invalidate_global_catalog_cache()' not in t: t=t.replace('    db.flush()\n    return offer\n','    db.flush()\n    invalidate_global_catalog_cache()\n    return offer\n',1)
 p.write_text(t,encoding='utf-8')
 p=ROOT/'app/services/v9_catalog_ingestion_service.py'; t=p.read_text(encoding='utf-8')
 if '_RUNNING_PLAN_IDS' not in t: t=t.replace('_LOCK = threading.RLock()\n','_LOCK = threading.RLock()\n_RUNNING_PLAN_IDS: set[str] = set()\n',1)
 old='def run_catalog_plan(plan: dict[str, Any]) -> dict[str, Any]:\n    run_id = str(uuid4())\n    started = _now()\n    plan_id = str(plan["id"])\n'
 new='def run_catalog_plan(plan: dict[str, Any]) -> dict[str, Any]:\n    run_id = str(uuid4())\n    started = _now()\n    plan_id = str(plan["id"])\n    with _LOCK:\n        if plan_id in _RUNNING_PLAN_IDS:\n            return {"run_id":run_id,"plan_id":plan_id,"plan_name":plan.get("name",plan_id),"status":"skipped_already_running","started_at":_iso(started),"finished_at":_iso(started),"duration_seconds":0,"store_count":0,"successful_store_count":0,"failed_store_count":0,"found_count":0,"saved_count":0,"updated_count":0,"new_global_products":0,"new_active_offers":0,"new_multi_store_products":0,"results":[]}\n        _RUNNING_PLAN_IDS.add(plan_id)\n'
 if 'skipped_already_running' not in t: t=t.replace(old,new,1)
 if '_RUNNING_PLAN_IDS.discard(plan_id)' not in t: t=t.replace('    return row\n\n\ndef run_plan_by_id','    with _LOCK:\n        _RUNNING_PLAN_IDS.discard(plan_id)\n    return row\n\n\ndef run_plan_by_id',1)
 p.write_text(t,encoding='utf-8')
 p=ROOT/'main.py'; t=p.read_text(encoding='utf-8'); imp='from app.web.admin_v9_performance_routes import router as admin_v9_performance_router\n'
 if imp not in t: t=imp+t
 inc='app.include_router(admin_v9_performance_router)\n'
 if inc not in t:
  pos=t.rfind('app.include_router('); end=t.find('\n',pos); t=t[:end+1]+inc+t[end+1:]
 p.write_text(t,encoding='utf-8')
 p=ROOT/'app/templates/base.html'; t=p.read_text(encoding='utf-8')
 if '/admin/v9-performance' not in t: t+='\n<!-- V9 Performans: /admin/v9-performance -->\n'
 p.write_text(t,encoding='utf-8'); print('V9.9 entegrasyonu tamamlandı.'); return 0
if __name__=='__main__': raise SystemExit(main())
