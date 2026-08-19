from __future__ import annotations
from app.services.workload_priority_v23612 import user_deep_priority_active_v23612, user_priority_generation_v23617

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, ProductOffer, RawProduct, Store
from app.services.multi_store_offer_repair_v14_service import product_from_global_product, repair_product_across_stores
from app.services.cross_store_search_service import STORE_SEARCH_DEFINITIONS
from app.services.catalog_reconciliation_service import sync_global_offer
from app.services.store_retry_intelligence_v2360 import store_retry_intelligence_v2360

ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT / '.runtime' / 'catalog_feed_store_state_v218.json'
LEGACY_STATE_FILE = ROOT / '.runtime' / 'catalog_feed_store_state_v217.json'
_lock = threading.RLock()

BACKOFF_HOURS = {
    'SUCCESS': 0.5,
    'PRODUCT_NOT_FOUND': 12.0,
    'SECURITY_CHALLENGE': 6.0,
    'ERROR': 2.0,
}


# V23.16: mağaza-geneli kısa devre. Özellikle SECURITY_CHALLENGE veren
# yavaş kaynakların her ürün için tekrar browser açmasını engeller.
_STORE_CIRCUIT_UNTIL: dict[str, datetime] = {}
_STORE_CIRCUIT_MINUTES = 10
FAST_STORE_TIER = {"pazarama", "teknosa", "mediamarkt", "n11", "vatan"}


def _utcnow() -> datetime:
    return datetime.utcnow()


def _retry_context_v23611(source: Any) -> str:
    return " | ".join(
        str(value or "").casefold().strip()
        for value in (
            getattr(source, "name", None),
            getattr(source, "brand", None),
            getattr(source, "model", None),
            getattr(source, "category", None),
        )
    )[:1000]


def _load() -> dict[str, Any]:
    for path in (STATE_FILE, LEGACY_STATE_FILE):
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    data['version'] = '21.8.0'
                    return data
        except Exception:
            pass
    return {'version': '21.8.0', 'products': {}}


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
    if 'NO_BUYABLE_OFFER' in msg:
        return 'NO_BUYABLE_OFFER'
    if (
        'KESİN RED' in msg
        or 'KESIN RED' in msg
        or 'RENK FARKLI' in msg
        or 'GÜVENLİ EŞLEŞME' in msg
        or 'GUVENLI ESLESME' in msg
        or 'EŞLEŞMESİ BULUNAMADI' in msg
    ):
        return 'IDENTITY_REJECT'
    if (
        'ADAY BULUNAMADI' in msg
        or 'ÜRÜN ADAYI BULUNAMADI' in msg
        or 'URUN ADAYI BULUNAMADI' in msg
        or 'NO_CANDIDATE' in msg
    ):
        return 'NO_CANDIDATE'
    if 'TIMEOUT' in msg or 'ZAMAN AŞIM' in msg:
        return 'TIMEOUT'
    return 'SCRAPE_ERROR'


def _active_offer_snapshot(product_id: int, store_codes: set[str] | None = None) -> dict[str, list[int]]:
    db = SessionLocal()
    try:
        query = db.query(GlobalOffer).filter(
            GlobalOffer.global_product_id == int(product_id),
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == 'ACTIVE',
            GlobalOffer.current_price > 0,
        )
        if store_codes:
            query = query.filter(GlobalOffer.store_code.in_(store_codes))
        result: dict[str, list[int]] = {}
        for offer in query.all():
            result.setdefault(str(offer.store_code).casefold(), []).append(int(offer.id))
        return result
    finally:
        db.close()


def _restore_failed_store_offers(product_id: int, snapshot: dict[str, list[int]], failed_codes: set[str]) -> int:
    ids = [offer_id for code, values in snapshot.items() if code in failed_codes for offer_id in values]
    if not ids:
        return 0
    db = SessionLocal()
    try:
        rows = db.query(GlobalOffer).filter(GlobalOffer.id.in_(ids), GlobalOffer.global_product_id == int(product_id)).all()
        restored = 0
        for offer in rows:
            if not (offer.is_active and not offer.is_hidden and offer.lifecycle_status == 'ACTIVE'):
                restored += 1
            offer.is_active = True
            offer.is_hidden = False
            offer.lifecycle_status = 'ACTIVE'
            offer.duplicate_reason = None
        gp = db.get(GlobalProduct, int(product_id))
        if gp is not None:
            gp.active_offer_count = db.query(GlobalOffer).filter(
                GlobalOffer.global_product_id == int(product_id),
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
                GlobalOffer.lifecycle_status == 'ACTIVE',
                GlobalOffer.current_price > 0,
            ).count()
            gp.updated_at = _utcnow()
        db.commit()
        return restored
    finally:
        db.close()


def _recover_global_offers_from_legacy(product_id: int) -> int:
    """Aynı DB içinde legacy teklif canlıysa eksik GlobalOffer'ı yeniden kurar.

    Bu işlem yalnızca raw kayıt zaten ilgili global ürüne bağlıysa yapılır; yeni kimlik
    veya ProductGroup üretmez.
    """
    db = SessionLocal()
    recovered = 0
    try:
        raws = db.query(RawProduct).filter(RawProduct.global_product_id == int(product_id)).all()
        for raw in raws:
            existing = db.query(GlobalOffer).filter(GlobalOffer.raw_product_id == raw.id).first()
            if existing is not None:
                continue
            if not raw.legacy_product_id:
                continue
            legacy_offer = (
                db.query(ProductOffer)
                .join(Store, Store.id == ProductOffer.store_id)
                .filter(
                    ProductOffer.product_id == raw.legacy_product_id,
                    ProductOffer.is_active.is_(True),
                    ProductOffer.is_hidden.is_(False),
                    Store.code == raw.store_code,
                    ProductOffer.current_price > 0,
                )
                .order_by(ProductOffer.updated_at.desc(), ProductOffer.id.desc())
                .first()
            )
            if legacy_offer is None:
                continue
            offer = sync_global_offer(db=db, raw=raw, legacy_offer=legacy_offer)
            if offer is not None:
                recovered += 1
        if recovered:
            db.commit()
        return recovered
    finally:
        db.close()


def _active_offer_details(product_id: int) -> dict[str, list[dict[str, Any]]]:
    db = SessionLocal()
    try:
        rows = db.query(GlobalOffer).filter(
            GlobalOffer.global_product_id == int(product_id),
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == 'ACTIVE',
            GlobalOffer.current_price > 0,
        ).order_by(GlobalOffer.store_code.asc(), GlobalOffer.current_price.asc()).all()
        result: dict[str, list[dict[str, Any]]] = {}
        for offer in rows:
            result.setdefault(str(offer.store_code).casefold(), []).append({
                'offer_id': int(offer.id),
                'price': float(offer.current_price or 0),
                'seller': offer.seller,
                'last_seen_at': offer.last_seen_at.isoformat() if offer.last_seen_at else None,
                'lifecycle_status': offer.lifecycle_status,
            })
        return result
    finally:
        db.close()


def get_offer_lifecycle_status(product_id: int) -> dict[str, Any]:
    product_id = int(product_id)
    recovered = _recover_global_offers_from_legacy(product_id)
    with _lock:
        state = _load()
        crawler = state.get('products', {}).get(str(product_id), {})
    offers = _active_offer_details(product_id)
    source = product_from_global_product(product_id)
    source_code = str(source.source_site or '').casefold()
    all_codes = [d.code for d in STORE_SEARCH_DEFINITIONS]
    searchable_codes = [code for code in all_codes if code != source_code]
    stores: dict[str, Any] = {}
    for code in all_codes:
        c = crawler.get(code, {})
        active = offers.get(code, [])
        stores[code] = {
            'crawler_status': c.get('status', 'NEVER_CHECKED'),
            'last_checked_at': c.get('last_checked_at'),
            'last_success_at': c.get('last_success_at'),
            'next_check_at': c.get('next_check_at'),
            'backoff_hours': c.get('backoff_hours'),
            'crawler_message': c.get('message'),
            'is_source_store': code == source_code,
            'is_searchable_store': code != source_code,
            'active_offer_count': len(active),
            'has_active_offer': bool(active),
            'offers': active,
            'serving_status': 'ACTIVE_OFFER' if active else 'NO_ACTIVE_OFFER',
        }
    return {
        'engine': 'FIRSATAI_OFFER_LIFECYCLE_STORE_STATE',
        'engine_version': '21.8.0',
        'global_product_id': product_id,
        'source_store_code': source_code or None,
        'tracked_store_count': len(all_codes),
        'searchable_store_count': len(searchable_codes),
        'active_offer_store_count': len(offers),
        'active_offer_store_codes': sorted(offers),
        'recovered_global_offer_count': recovered,
        'crawler_state_is_separate_from_offer_state': True,
        'stores': stores,
    }


def smart_refresh_product(*, global_product_id: int, candidate_limit: int = 50, parallel_workers: int = 3, force: bool = False, allowed_store_codes: set[str] | None = None, fast_mode: bool = False, workload_class: str = "BACKGROUND") -> dict[str, Any]:
    product_id = int(global_product_id)
    workload_class_v23614 = str(workload_class or "BACKGROUND").upper()

    if (
        workload_class_v23614 != "USER_INGESTION"
        and user_deep_priority_active_v23612()
    ):
        print(
            "V23.61.4 CENTRAL SMART REFRESH YIELD:",
            f"global_product_id={product_id}",
            f"workload={workload_class_v23614}",
            "reason=USER_INGESTION_PRIORITY_ACTIVE",
        )
        return {
            "success": True,
            "global_product_id": product_id,
            "smart_refresh": True,
            "priority_yielded": True,
            "priority_yield_reason": "USER_INGESTION_PRIORITY_ACTIVE",
            "workload_class": workload_class_v23614,
            "scanned_store_count": 0,
            "skipped_store_count": 0,
            "due_stores": [],
            "skipped_stores": [],
            "newly_saved_offer_count": 0,
            "store_results": [],
            "results": [],
        }

    _recover_global_offers_from_legacy(product_id)
    now = _utcnow()
    source = product_from_global_product(product_id)
    source_code = str(source.source_site or '').casefold()

    with _lock:
        state = _load()
        product_state = state.setdefault('products', {}).setdefault(str(product_id), {})

    all_codes = [d.code for d in STORE_SEARCH_DEFINITIONS]
    searchable_codes = [code for code in all_codes if code != source_code]
    # V23.62.68: preserve the original cross-store budget before the N11
    # force-only observability reinsert. Without this guard, source=n11 could
    # turn an 11-store cross-store scan into 12 stores (11 generic + N11),
    # making a real Amazon offer look like a regression against an invalid
    # store-count contract. Candidate acceptance is unchanged.
    force_store_budget_v236268 = len(searchable_codes)

    # V23.63.04: localhost force/USER_INGESTION observability must keep both
    # N11 and the newly-added Turkcell Pasaj in the due-set even if either one
    # is the current source store. Production/background behavior is unchanged.
    protected_force_codes_v236304 = ("n11", "turkcellpasaj")
    for protected_code_v236304 in protected_force_codes_v236304:
        force_due_inclusion_v236304 = (
            bool(force)
            and workload_class_v23614 == "USER_INGESTION"
            and protected_code_v236304 in all_codes
            and protected_code_v236304 not in searchable_codes
        )
        if force_due_inclusion_v236304:
            searchable_codes.append(protected_code_v236304)
            marker_v236304 = (
                "V23.62.65 N11 FORCE DUE-SET INCLUSION:"
                if protected_code_v236304 == "n11"
                else "V23.63.04 TURKCELL FORCE DUE-SET INCLUSION:"
            )
            print(
                marker_v236304,
                "forced=True",
                f"source_store={source_code}",
                f"{protected_code_v236304}_due=True",
            )

    if allowed_store_codes is not None:
        allowed = {str(code).casefold() for code in allowed_store_codes}
        searchable_codes = [code for code in searchable_codes if code.casefold() in allowed]

    # V23.62.68: N11 force observability consumes one of the existing
    # cross-store slots; it is never a 12th store. When the source is N11 and
    # the reinsert grows the due-set past the original budget, deterministically
    # evict the lowest static-priority tail store (the final non-N11 code in the
    # registry order). Lower cross-store adaptive ordering remains unchanged.
    if (
        bool(force)
        and workload_class_v23614 == "USER_INGESTION"
        and any(code_v236304 in searchable_codes for code_v236304 in protected_force_codes_v236304)
        and len(searchable_codes) > force_store_budget_v236268
    ):
        dropped_store_v236268 = None
        for code_v236268 in reversed(searchable_codes):
            if code_v236268 not in set(protected_force_codes_v236304):
                dropped_store_v236268 = code_v236268
                break
        if dropped_store_v236268 is not None:
            searchable_codes = [
                code_v236268 for code_v236268 in searchable_codes
                if code_v236268 != dropped_store_v236268
            ]
        print(
            "V23.62.68 FORCE STORE-BUDGET CONTRACT:",
            f"budget={force_store_budget_v236268}",
            f"final={len(searchable_codes)}",
            f"n11_present={'n11' in searchable_codes}",
            f"turkcell_present={'turkcellpasaj' in searchable_codes}",
            f"dropped={dropped_store_v236268}",
        )

    # V23.16.1 hotfix: circuit_skipped must be initialized inside the
    # smart-refresh execution path that consumes it. Keeping this state local
    # also prevents lifecycle-status reads from depending on refresh-only vars.
    circuit_skipped: list[dict[str, Any]] = []
    if not force:
        active_codes: list[str] = []
        for code in searchable_codes:
            until = _STORE_CIRCUIT_UNTIL.get(code.casefold())
            if until is not None and until > now:
                circuit_skipped.append({
                    'store_code': code,
                    'reason': 'GLOBAL_CIRCUIT_BREAKER',
                    'next_check_at': until.isoformat(),
                })
            else:
                active_codes.append(code)
        searchable_codes = active_codes

    due: list[str] = []
    skipped: list[dict[str, Any]] = list(circuit_skipped)
    retry_context_v23611 = _retry_context_v23611(source)
    for code in searchable_codes:
        row = product_state.get(code, {})
        next_check = None
        if row.get('next_check_at'):
            try:
                next_check = datetime.fromisoformat(row['next_check_at'])
            except ValueError:
                pass

        retry_mode = str(row.get('retry_mode') or '').upper()
        same_context = str(row.get('retry_context') or '') == retry_context_v23611

        if (
            not force
            and retry_mode == 'CONTEXT_CHANGE_ONLY'
            and same_context
        ):
            skipped.append({
                'store_code': code,
                'reason': 'RELIABILITY_CONTEXT_CHANGE_ONLY',
                'last_status': row.get('status'),
                'failure_class': row.get('failure_class'),
                'reliability_score': row.get('reliability_score'),
                'retry_mode': retry_mode,
                'retry_after_seconds': None,
                'next_check_at': None,
                'recommended_action': row.get('recommended_action'),
                'retry_reason': row.get('retry_reason'),
            })
        elif force or next_check is None or next_check <= now:
            due.append(code)
        else:
            remaining = max(0, int((next_check - now).total_seconds()))
            skipped.append({
                'store_code': code,
                'reason': 'RELIABILITY_BACKOFF_ACTIVE',
                'next_check_at': row.get('next_check_at'),
                'last_status': row.get('status'),
                'failure_class': row.get('failure_class'),
                'reliability_score': row.get('reliability_score'),
                'retry_mode': row.get('retry_mode'),
                'retry_after_seconds': row.get('retry_after_seconds'),
                'retry_after_remaining_seconds': remaining,
                'recommended_action': row.get('recommended_action'),
                'retry_reason': row.get('retry_reason'),
            })

    if not due:
        lifecycle = get_offer_lifecycle_status(product_id)
        return {
            'success': True,
            'global_product_id': product_id,
            'smart_refresh': True,
            'scanned_store_count': 0,
            'skipped_store_count': len(skipped),
            'tracked_store_count': lifecycle['tracked_store_count'],
            'searchable_store_count': lifecycle['searchable_store_count'],
            'due_stores': [],
            'skipped_stores': skipped,
            'active_store_codes': lifecycle['active_offer_store_codes'],
            'active_offer_store_count': lifecycle['active_offer_store_count'],
            'retention_restored_offer_count': 0,
        }

    due_set = set(due)
    snapshot = _active_offer_snapshot(product_id, due_set)
    scan = repair_product_across_stores(
        source_product=source,
        target_global_product_id=product_id,
        candidate_limit=max(5, min(int(candidate_limit), 100)),
        parallel_workers=max(1, min(int(parallel_workers), 6)),
        allowed_store_codes=due_set,
        fast_mode=bool(fast_mode),
        workload_class=workload_class_v23614,
    )

    seen: set[str] = set()
    failed_codes: set[str] = set()
    with _lock:
        state = _load()
        product_state = state.setdefault('products', {}).setdefault(str(product_id), {})
        for result in scan.get('results', []):
            code = str(result.get('store_code') or '').casefold()
            if not code:
                continue
            seen.add(code)
            status = _classify(result)
            if status == 'SECURITY_CHALLENGE':
                _STORE_CIRCUIT_UNTIL[code] = now + timedelta(minutes=_STORE_CIRCUIT_MINUTES)
            elif status == 'SUCCESS':
                _STORE_CIRCUIT_UNTIL.pop(code, None)
            if status != 'SUCCESS':
                failed_codes.add(code)

            retry_intel_v23611 = store_retry_intelligence_v2360(
                success=(status == 'SUCCESS'),
                failure_class=None if status == 'SUCCESS' else status,
            )
            retry_mode_v23611 = str(retry_intel_v23611.get('retry_mode') or 'NONE').upper()
            retry_after_v23611 = retry_intel_v23611.get('retry_after_seconds')

            # Başarılı mağazalarda mevcut 30 dk freshness davranışı korunur.
            # Failure'larda v23.60 retry policy tek kaynak olur.
            if status == 'SUCCESS':
                next_check_at_v23611 = now + timedelta(minutes=30)
            elif retry_mode_v23611 in {'DEFERRED', 'TRANSIENT'} and retry_after_v23611 is not None:
                next_check_at_v23611 = now + timedelta(seconds=float(retry_after_v23611))
            else:
                next_check_at_v23611 = None

            # V23.61.11: v23.60 retry-intelligence refactorundan sonra eski
            # `hours` lokal değişkeni artık yoktu. Persist edilen backoff değeri
            # retry_after_seconds tek kaynağından güvenli biçimde türetilir.
            backoff_hours_v236111 = (
                round(float(retry_after_v23611) / 3600.0, 6)
                if retry_after_v23611 is not None
                else None
            )

            previous = product_state.get(code, {})
            product_state[code] = {
                'status': status,
                'failure_class': None if status == 'SUCCESS' else status,
                'last_checked_at': now.isoformat(),
                'reliability_score': retry_intel_v23611.get('reliability_score'),
                'retryable': retry_intel_v23611.get('retryable'),
                'retry_mode': retry_mode_v23611,
                'retry_after_seconds': retry_after_v23611,
                'recommended_action': retry_intel_v23611.get('recommended_action'),
                'retry_reason': retry_intel_v23611.get('reason'),
                'retry_context': retry_context_v23611,
                'last_success_at': now.isoformat() if status == 'SUCCESS' else previous.get('last_success_at'),
                'next_check_at': next_check_at_v23611.isoformat() if next_check_at_v23611 is not None else None,
                'backoff_hours': backoff_hours_v236111,
                'message': result.get('message'),
            }
        for code in due:
            if code not in seen:
                failed_codes.add(code)
                product_state[code] = {
                    'status': 'ERROR',
                    'last_checked_at': now.isoformat(),
                    'last_success_at': product_state.get(code, {}).get('last_success_at'),
                    'next_check_at': (now + timedelta(hours=BACKOFF_HOURS['ERROR'])).isoformat(),
                    'backoff_hours': BACKOFF_HOURS['ERROR'],
                    'message': 'Mağaza sonucu dönmedi.',
                }
        state['version'] = '21.8.0'
        state['updated_at'] = _utcnow().isoformat()
        _save(state)

    restored = _restore_failed_store_offers(product_id, snapshot, failed_codes)
    lifecycle = get_offer_lifecycle_status(product_id)
    return {
        'success': True,
        'global_product_id': product_id,
        'smart_refresh': True,
        'refresh_mode': 'FAST' if fast_mode else 'DEEP',
        'force': bool(force),
        'scanned_store_count': int(scan.get('searched_store_count', 0)),
        'skipped_store_count': len(skipped),
        'tracked_store_count': lifecycle['tracked_store_count'],
        'searchable_store_count': lifecycle['searchable_store_count'],
        'due_stores': due,
        'skipped_stores': skipped,
        'newly_saved_offer_count': int(scan.get('newly_saved_offer_count', 0) or 0),
        'active_offer_count': sum(len(v) for v in _active_offer_details(product_id).values()),
        'active_store_codes': lifecycle['active_offer_store_codes'],
        'active_offer_store_count': lifecycle['active_offer_store_count'],
        'retention_restored_offer_count': restored,
        'store_results': scan.get('results', []),
    }


def smart_refresh_batch(*, product_ids: list[int], candidate_limit: int = 50, parallel_workers: int = 3) -> dict[str, Any]:
    results = []
    deferred_product_ids = []
    batch_generation_v23617 = user_priority_generation_v23617()
    yield_reason_v23617 = None

    for offset, product_id in enumerate(product_ids):
        current_generation_v23617 = user_priority_generation_v23617()
        if (
            user_deep_priority_active_v23612()
            or current_generation_v23617 != batch_generation_v23617
        ):
            deferred_product_ids = [int(value) for value in product_ids[offset:]]
            yield_reason_v23617 = (
                "USER_INGESTION_PRIORITY_ACTIVE"
                if user_deep_priority_active_v23612()
                else "USER_PRIORITY_GENERATION_CHANGED"
            )
            print(
                "V23.61.7 BACKGROUND BATCH GENERATION YIELD:",
                f"start_generation={batch_generation_v23617}",
                f"current_generation={current_generation_v23617}",
                f"reason={yield_reason_v23617}",
                f"deferred={deferred_product_ids}",
            )
            break

        try:
            results.append(
                smart_refresh_product(
                    global_product_id=int(product_id),
                    candidate_limit=candidate_limit,
                    parallel_workers=parallel_workers,
                    force=False,
                    workload_class="BACKGROUND",
                )
            )
        except Exception as error:
            results.append({
                'success': False,
                'global_product_id': int(product_id),
                'error': f'{type(error).__name__}: {error}',
            })

        # V23.61.7: ürün tamamlandıktan sonra kullanıcı generation değişmişse
        # sonraki background ürüne geçmeden kesin yield.
        post_generation_v23617 = user_priority_generation_v23617()
        if post_generation_v23617 != batch_generation_v23617:
            deferred_product_ids = [int(value) for value in product_ids[offset + 1:]]
            if deferred_product_ids:
                yield_reason_v23617 = "USER_PRIORITY_GENERATION_CHANGED_AFTER_PRODUCT"
                print(
                    "V23.61.7 BACKGROUND BATCH POST-PRODUCT YIELD:",
                    f"completed_product={int(product_id)}",
                    f"start_generation={batch_generation_v23617}",
                    f"current_generation={post_generation_v23617}",
                    f"deferred={deferred_product_ids}",
                )
            break

    return {
        'engine_version': '23.61.7',
        'product_count': len(product_ids),
        'executed_product_count': len(results),
        'deferred_product_count': len(deferred_product_ids),
        'deferred_product_ids': deferred_product_ids,
        'yield_reason': yield_reason_v23617 if deferred_product_ids else None,
        'batch_priority_generation': batch_generation_v23617,
        'final_priority_generation': user_priority_generation_v23617(),
        'results': results,
    }
