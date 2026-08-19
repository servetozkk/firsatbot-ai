from pathlib import Path
r=Path(__file__).resolve().parents[2]
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.61.9"),
("background workload",'workload_class="BACKGROUND_DEEP_REFRESH"' in p),
("foreground released before queue",'mark_user_deep_done_v23612(str(task_id))' in p and 'BACKGROUND_DEEP_REFRESH_QUEUED' in p),
("no deep mark running",'queue_wait_v23612 = mark_user_deep_running_v23612' not in p),
("no deep lease heartbeat",'V23.61.6: cross-process lease heartbeat / reassert immediately before' not in p),
("foreground defer","V23.61.9 DEEP REFRESH DEFER" in p),
("timer resubmit","Timer(" in p and "_resubmit_background_deep_refresh_v23619" in p),
("queue reason","FOREGROUND_USER_INGESTION_ACTIVE" in p),
("runtime","/api/runtime-identity/v23619" in m),
("v23618 preserved","/api/runtime-identity/v23618" in m),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
