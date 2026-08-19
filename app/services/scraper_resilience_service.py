from __future__ import annotations

import json
import random
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from app.services.operational_log_service import record_operation_event

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "data" / "scraper_health_state.json"
DLQ_PATH = ROOT / "data" / "scraper_dead_letter.json"
_LOCK = threading.RLock()

STORE_POLICIES = {
    "trendyol": {"retries": 3, "base_delay": 2.0, "failure_threshold": 4, "cooldown_minutes": 20},
    "hepsiburada": {"retries": 2, "base_delay": 2.0, "failure_threshold": 4, "cooldown_minutes": 20},
    "amazon": {"retries": 3, "base_delay": 3.0, "failure_threshold": 4, "cooldown_minutes": 30},
    "n11": {"retries": 2, "base_delay": 3.0, "failure_threshold": 3, "cooldown_minutes": 30},
    "mediamarkt": {"retries": 3, "base_delay": 3.0, "failure_threshold": 3, "cooldown_minutes": 30},
    "default": {"retries": 2, "base_delay": 1.5, "failure_threshold": 5, "cooldown_minutes": 15},
}

class ScraperCircuitOpenError(RuntimeError):
    pass

def _read(path: Path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return default

def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    tmp.replace(path)

def _iso(value=None): return (value or datetime.utcnow()).isoformat(timespec='seconds')

def store_code_from_url(url: str) -> str:
    host=str(urlsplit(str(url or '')).hostname or '').casefold()
    mapping={'trendyol.com':'trendyol','hepsiburada.com':'hepsiburada','amazon.com.tr':'amazon','n11.com':'n11','mediamarkt.com.tr':'mediamarkt','teknosa.com':'teknosa','vatanbilgisayar.com':'vatan','pazarama.com':'pazarama','idefix.com':'idefix','pttavm.com':'pttavm','beymen.com':'beymen'}
    for domain,code in mapping.items():
        if host==domain or host.endswith('.'+domain): return code
    return host.split('.')[0] or 'unknown'

def classify_scraper_error(error: Exception):
    text=f'{type(error).__name__}: {error}'.casefold()
    if any(x in text for x in ('404','410','arama sonuçları','ürün bağlantısı')): return 'permanent',False
    if any(x in text for x in ('403','429','timeout','timed out','connection','dns','502','503','504','targetclosed','network','ssl')): return 'transient',True
    return 'unknown',True

def _policy(code): return dict(STORE_POLICIES.get(code,STORE_POLICIES['default']))

def get_store_health(store_code: str):
    with _LOCK: row=_read(STATE_PATH,{}).get(store_code,{})
    opened=row.get('opened_until'); is_open=False
    if opened:
        try: is_open=datetime.fromisoformat(opened)>datetime.utcnow()
        except ValueError: pass
    success=int(row.get('success_count',0)); failure=int(row.get('failure_count',0)); total=success+failure
    rate=round(success/total*100,2) if total else 100.0
    score=max(0.0,min(100.0,rate-int(row.get('consecutive_failures',0))*8))
    return {'store_code':store_code,'status':'CIRCUIT_OPEN' if is_open else 'HEALTHY','health_score':round(score,2),'success_count':success,'failure_count':failure,'success_rate':rate,'consecutive_failures':int(row.get('consecutive_failures',0)),'last_success_at':row.get('last_success_at'),'last_failure_at':row.get('last_failure_at'),'last_error':row.get('last_error'),'opened_until':opened,'average_duration_ms':round(float(row.get('average_duration_ms',0)),2)}

def all_store_health():
    with _LOCK: codes=set(_read(STATE_PATH,{}))
    codes.update(k for k in STORE_POLICIES if k!='default')
    return sorted((get_store_health(c) for c in codes),key=lambda x:(x['status']!='CIRCUIT_OPEN',x['health_score'],x['store_code']))

def assert_circuit_closed(store_code: str):
    h=get_store_health(store_code)
    if h['status']=='CIRCUIT_OPEN': raise ScraperCircuitOpenError(f"{store_code} devresi açık; yeniden deneme {h['opened_until']}")

def _record(store_code: str, success: bool, duration_ms: float, error: Exception|None=None):
    p=_policy(store_code)
    with _LOCK:
        state=_read(STATE_PATH,{}); row=state.setdefault(store_code,{})
        count=int(row.get('duration_sample_count',0)); avg=float(row.get('average_duration_ms',0))
        row['average_duration_ms']=(avg*count+duration_ms)/(count+1); row['duration_sample_count']=count+1
        if success:
            row['success_count']=int(row.get('success_count',0))+1; row['consecutive_failures']=0; row['last_success_at']=_iso(); row['last_error']=None; row['opened_until']=None
        else:
            row['failure_count']=int(row.get('failure_count',0))+1; row['consecutive_failures']=int(row.get('consecutive_failures',0))+1; row['last_failure_at']=_iso(); row['last_error']=f'{type(error).__name__}: {error}'
            if row['consecutive_failures']>=int(p['failure_threshold']):
                row['opened_until']=_iso(datetime.utcnow()+timedelta(minutes=int(p['cooldown_minutes'])))
                record_operation_event(level='WARNING',source='scraper_resilience',event_type='circuit_opened',message=f'{store_code} devresi açıldı.',details={'opened_until':row['opened_until'],'error':row['last_error']})
        _write(STATE_PATH,state)

def add_dead_letter(store_code: str,url: str,error: Exception,attempts: int,context: str):
    classification,retryable=classify_scraper_error(error)
    with _LOCK:
        rows=_read(DLQ_PATH,[]); rows=rows if isinstance(rows,list) else []
        rows.append({'id':f'dlq-{int(time.time()*1000)}-{random.randint(100,999)}','created_at':_iso(),'store_code':store_code,'url':url,'context':context,'error':f'{type(error).__name__}: {error}','classification':classification,'retryable':retryable,'attempts':attempts,'status':'PENDING'})
        _write(DLQ_PATH,rows[-2000:])
    record_operation_event(level='ERROR',source='scraper_resilience',event_type='dead_letter_added',message=f'{store_code} URL dead-letter kuyruğuna alındı.',details={'url':url,'error':str(error)})

def read_dead_letters(limit: int=300):
    with _LOCK: rows=_read(DLQ_PATH,[])
    return list(reversed(rows[-max(1,min(limit,2000)):])) if isinstance(rows,list) else []

def clear_dead_letters():
    with _LOCK:
        rows=_read(DLQ_PATH,[]); count=len(rows) if isinstance(rows,list) else 0; DLQ_PATH.unlink(missing_ok=True)
    return count

def resilient_call(*,store_code: str,url: str,operation: Callable[[],Any],requested_retries: int|None=None,context: str='product_detail'):
    assert_circuit_closed(store_code); p=_policy(store_code); retries=max(int(requested_retries or 0),int(p['retries'])); last=None
    for attempt in range(retries+1):
        started=time.perf_counter()
        try:
            value=operation(); _record(store_code,True,(time.perf_counter()-started)*1000)
            if attempt: record_operation_event(level='INFO',source='scraper_resilience',event_type='recovered_after_retry',message=f'{store_code} {attempt+1}. denemede kurtarıldı.',details={'url':url})
            return value
        except Exception as error:
            last=error; _record(store_code,False,(time.perf_counter()-started)*1000,error); classification,retryable=classify_scraper_error(error)
            if attempt>=retries or not retryable: break
            delay=float(p['base_delay'])*(2**attempt)+random.uniform(.1,.5)
            record_operation_event(level='WARNING',source='scraper_resilience',event_type='retry_scheduled',message=f'{store_code} yeniden denenecek.',details={'url':url,'attempt':attempt+1,'delay_seconds':round(delay,2),'classification':classification})
            time.sleep(delay)
    assert last is not None
    add_dead_letter(store_code,url,last,retries+1,context)
    raise last
