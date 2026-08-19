from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.database.database import SessionLocal
from app.database.models import GlobalOffer
from app.services.multi_store_offer_repair_v14_service import product_from_global_product, repair_product_across_stores
from app.services.cross_store_search_service import STORE_SEARCH_DEFINITIONS

ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT / '.runtime' / 'catalog_feed_store_state_v217.json'
_lock = threading.RLock()

def _utcnow() -> datetime:
    return datetime.utcnow()


BACKOFF_HOURS = {
    'SUCCESS': 0.5,
    'PRODUCT_NOT_FOUND': 12.0,
    'SECURITY_CHALLENGE': 6.0,
    'ERROR': 2.0,
}


def _load() -> dict[str, Any]:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except Exception:
        pass
    return {'version': '21.7.0', 'products': {}}


def _save(data: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(STATE_FILE)


def _classify(row: dict[str, Any]) -> str:
    if bool(row.get('success')):
        return 'SUCCESS'
    msg = str(row.get('message') or '').upper()
    if 'SECURITY_CHALLENGE' in msg or 'CLOUDFLARE' in msg:
        return 'SECURITY_CHALLENGE'
    if 'ADAY BULUNAMADI' in msg or 'ÜRÜN ADAYI BULUNAMADI' in msg or 'URUN ADAYI BULUNAMADI' in msg:
        return 'PRODUCT_NOT_FOUND'
    return 'ERROR'


def _existing_store_codes(product_id: int) -> set[str]:
    db = SessionLocal()
    try:
        rows = db.query(GlobalOffer.store_code).filter(
            GlobalOffer.global_product_id == int(product_id),
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
        ).distinct().all()
        return {str(r[0]).casefold() for r in rows if r and r[0]}
    finally:
        db.close()


def get_smart_refresh_status(product_id: int | None = None) -> dict[str, Any]:
    with _lock:
        data = _load()
    if product_id is None:
        return data
    return {
        'version': data.get('version', '21.7.0'),
        'global_product_id': int(product_id),
        'stores': data.get('products', {}).get(str(int(product_id)), {}),
    }


def smart_refresh_product(*, global_product_id: int, candidate_limit: int = 50, parallel_workers: int = 3, force: bool = False) -> dict[str, Any]:
    product_id = int(global_product_id)
    now = _utcnow()
    with _lock:
        state = _load()
        product_state = state.setdefault('products', {}).setdefault(str(product_id), {})

    all_codes = [d.code for d in STORE_SEARCH_DEFINITIONS]
    due: list[str] = []
    skipped: list[dict[str, Any]] = []
    for code in all_codes:
        row = product_state.get(code, {})
        next_check_raw = row.get('next_check_at')
        next_check = None
        if next_check_raw:
            try:
                next_check = datetime.fromisoformat(next_check_raw)
            except ValueError:
                next_check = None
        if force or next_check is None or next_check <= now:
            due.append(code)
        else:
            skipped.append({'store_code': code, 'reason': 'BACKOFF_ACTIVE', 'next_check_at': next_check_raw, 'last_status': row.get('status')})

    if not due:
        return {
            'success': True, 'global_product_id': product_id, 'smart_refresh': True,
            'scanned_store_count': 0, 'skipped_store_count': len(skipped), 'due_stores': [],
            'skipped_stores': skipped, 'active_store_codes': sorted(_existing_store_codes(product_id)),
        }

    source = product_from_global_product(product_id)
    scan = repair_product_across_stores(
        source_product=source,
        target_global_product_id=product_id,
        candidate_limit=max(5, min(int(candidate_limit), 100)),
        parallel_workers=max(1, min(int(parallel_workers), 6)),
        allowed_store_codes=set(due),
    )

    seen = set()
    with _lock:
        state = _load()
        product_state = state.setdefault('products', {}).setdefault(str(product_id), {})
        for result in scan.get('results', []):
            code = str(result.get('store_code') or '').casefold()
            if not code:
                continue
            seen.add(code)
            status = _classify(result)
            hours = BACKOFF_HOURS[status]
            previous = product_state.get(code, {})
            product_state[code] = {
                'status': status,
                'last_checked_at': now.isoformat(),
                'last_success_at': now.isoformat() if status == 'SUCCESS' else previous.get('last_success_at'),
                'next_check_at': (now + timedelta(hours=hours)).isoformat(),
                'backoff_hours': hours,
                'message': result.get('message'),
            }
        for code in due:
            if code not in seen:
                product_state[code] = {
                    'status': 'ERROR', 'last_checked_at': now.isoformat(),
                    'last_success_at': product_state.get(code, {}).get('last_success_at'),
                    'next_check_at': (now + timedelta(hours=BACKOFF_HOURS['ERROR'])).isoformat(),
                    'backoff_hours': BACKOFF_HOURS['ERROR'], 'message': 'Mağaza sonucu dönmedi.',
                }
        state['version'] = '21.7.0'
        state['updated_at'] = _utcnow().isoformat()
        _save(state)

    return {
        'success': True,
        'global_product_id': product_id,
        'smart_refresh': True,
        'force': bool(force),
        'scanned_store_count': int(scan.get('searched_store_count', 0)),
        'skipped_store_count': len(skipped),
        'due_stores': due,
        'skipped_stores': skipped,
        'newly_saved_offer_count': int(scan.get('newly_saved_offer_count', 0) or 0),
        'active_offer_count': int(scan.get('active_offer_count', 0) or 0),
        'active_store_codes': scan.get('stores', []),
        'store_results': scan.get('results', []),
    }


def smart_refresh_batch(*, product_ids: list[int], candidate_limit: int = 50, parallel_workers: int = 3) -> dict[str, Any]:
    results = []
    for product_id in product_ids:
        try:
            results.append(smart_refresh_product(global_product_id=int(product_id), candidate_limit=candidate_limit, parallel_workers=parallel_workers, force=False))
        except Exception as error:
            results.append({"success": False, "global_product_id": int(product_id), "error": f"{type(error).__name__}: {error}"})
    return {"engine_version": "21.7.0", "product_count": len(product_ids), "results": results}
