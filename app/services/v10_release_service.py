from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import distinct, func, text

from app.database.models import (
    GlobalOffer,
    GlobalOfferPriceHistory,
    GlobalPriceAlert,
    GlobalProduct,
    GlobalProductVariant,
    RawProduct,
)
from app.database.v9_models import ProductMatchReview
from app.services.performance_cache_service import (
    global_cache_stats,
    invalidate_global_catalog_cache,
)
from app.services.v9_catalog_ingestion_service import (
    get_schedule_state,
    ingestion_history,
)
from app.services.v9_ingestion_runtime import (
    v9_ingestion_scheduler_status,
)
from app.services.v9_performance_service import (
    database_performance_snapshot,
)


def _valid_http_url(value: str | None) -> bool:
    try:
        parsed = urlparse(str(value or ''))
        return parsed.scheme in {'http', 'https'} and bool(parsed.netloc)
    except ValueError:
        return False


def _count_multi_store_products(db) -> int:
    return (
        db.query(GlobalOffer.global_product_id)
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == 'ACTIVE',
            GlobalOffer.current_price > 0,
        )
        .group_by(GlobalOffer.global_product_id)
        .having(func.count(distinct(GlobalOffer.store_code)) >= 2)
        .count()
    )


def build_release_diagnostics(
    db,
    *,
    require_live_scheduler: bool = False,
) -> dict[str, Any]:
    now = datetime.utcnow()
    stale_limit = now - timedelta(hours=24)

    global_products = db.query(GlobalProduct).count()
    global_variants = db.query(GlobalProductVariant).count()
    raw_products = db.query(RawProduct).count()
    global_offers = db.query(GlobalOffer).count()
    active_offers = (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == 'ACTIVE',
            GlobalOffer.current_price > 0,
        )
        .count()
    )

    orphan_raw = (
        db.query(RawProduct)
        .filter(
            RawProduct.reconciliation_status == 'MATCHED',
            RawProduct.global_product_id.is_(None),
        )
        .count()
    )
    orphan_variants = (
        db.query(GlobalProductVariant)
        .outerjoin(
            GlobalProduct,
            GlobalProduct.id == GlobalProductVariant.global_product_id,
        )
        .filter(GlobalProduct.id.is_(None))
        .count()
    )
    orphan_offers = (
        db.query(GlobalOffer)
        .outerjoin(
            GlobalProduct,
            GlobalProduct.id == GlobalOffer.global_product_id,
        )
        .filter(GlobalProduct.id.is_(None))
        .count()
    )
    wrong_variant_product = (
        db.query(GlobalOffer)
        .join(
            GlobalProductVariant,
            GlobalProductVariant.id == GlobalOffer.global_variant_id,
        )
        .filter(
            GlobalOffer.global_variant_id.is_not(None),
            GlobalOffer.global_product_id
            != GlobalProductVariant.global_product_id,
        )
        .count()
    )
    invalid_prices = (
        db.query(GlobalOffer)
        .filter(GlobalOffer.current_price <= 0)
        .count()
    )
    invalid_urls = sum(
        1
        for (value,) in db.query(GlobalOffer.url).all()
        if not _valid_http_url(value)
    )
    missing_images = (
        db.query(GlobalProduct)
        .filter(
            (GlobalProduct.primary_image.is_(None))
            | (func.trim(GlobalProduct.primary_image) == '')
        )
        .count()
    )
    review_queue = (
        db.query(ProductMatchReview)
        .filter(ProductMatchReview.status == 'PENDING')
        .count()
    )
    reconciliation_failures = (
        db.query(RawProduct)
        .filter(
            RawProduct.reconciliation_status.in_(
                ['FAILED', 'INVALID', 'REVIEW_REQUIRED']
            )
        )
        .count()
    )
    offers_without_history = (
        db.query(GlobalOffer)
        .outerjoin(
            GlobalOfferPriceHistory,
            GlobalOfferPriceHistory.global_offer_id == GlobalOffer.id,
        )
        .group_by(GlobalOffer.id)
        .having(func.count(GlobalOfferPriceHistory.id) == 0)
        .count()
    )
    duplicate_active_store_offers = (
        db.query(
            GlobalOffer.global_product_id,
            GlobalOffer.store_code,
        )
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == 'ACTIVE',
        )
        .group_by(
            GlobalOffer.global_product_id,
            GlobalOffer.store_code,
        )
        .having(func.count(GlobalOffer.id) > 1)
        .count()
    )
    stale_active_offers = (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.last_seen_at < stale_limit,
        )
        .count()
    )

    product_counts = dict(
        db.query(
            RawProduct.global_product_id,
            func.count(RawProduct.id),
        )
        .filter(RawProduct.global_product_id.is_not(None))
        .group_by(RawProduct.global_product_id)
        .all()
    )
    offer_counts = dict(
        db.query(
            GlobalOffer.global_product_id,
            func.count(GlobalOffer.id),
        )
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == 'ACTIVE',
            GlobalOffer.current_price > 0,
        )
        .group_by(GlobalOffer.global_product_id)
        .all()
    )
    counter_mismatches = 0
    for product in db.query(GlobalProduct).all():
        if int(product.raw_product_count or 0) != int(product_counts.get(product.id, 0)):
            counter_mismatches += 1
        if int(product.active_offer_count or 0) != int(offer_counts.get(product.id, 0)):
            counter_mismatches += 1

    scheduler = v9_ingestion_scheduler_status()
    schedule_state = get_schedule_state()
    recent_ingestion = ingestion_history(10)
    recent_failed_runs = sum(
        1
        for item in recent_ingestion
        if item.get('status') not in {'completed'}
    )
    database = database_performance_snapshot()
    cache = global_cache_stats()

    critical = {
        'orphan_offers': orphan_offers,
        'wrong_variant_product': wrong_variant_product,
        'invalid_prices': invalid_prices,
        'duplicate_active_store_offers': duplicate_active_store_offers,
    }
    warnings = {
        'orphan_raw': orphan_raw,
        'orphan_variants': orphan_variants,
        'invalid_urls': invalid_urls,
        'missing_images': missing_images,
        'review_queue': review_queue,
        'reconciliation_failures': reconciliation_failures,
        'offers_without_history': offers_without_history,
        'counter_mismatches': counter_mismatches,
        'stale_active_offers': stale_active_offers,
        'recent_failed_runs': recent_failed_runs,
    }
    critical_count = sum(critical.values())
    warning_count = sum(warnings.values())

    scheduler_required = bool(require_live_scheduler)
    scheduler_blocking = (
        scheduler_required
        and not bool(scheduler.get('running'))
    )

    release_gates = {
        'critical_data_errors': critical_count > 0,
        'live_scheduler_required': scheduler_required,
        'live_scheduler_running': bool(scheduler.get('running')),
        'scheduler_blocking': scheduler_blocking,
    }

    status = 'READY'
    if critical_count > 0 or scheduler_blocking:
        status = 'BLOCKED'
    elif warning_count > 0:
        status = 'READY_WITH_WARNINGS'

    return {
        'status': status,
        'checked_at': now.isoformat(timespec='seconds'),
        'summary': {
            'raw_products': raw_products,
            'global_products': global_products,
            'global_variants': global_variants,
            'global_offers': global_offers,
            'active_offers': active_offers,
            'multi_store_products': _count_multi_store_products(db),
            'critical_count': critical_count,
            'warning_count': warning_count,
        },
        'critical': critical,
        'warnings': warnings,
        'scheduler': scheduler,
        'release_gates': release_gates,
        'diagnostic_mode': (
            'LIVE_APPLICATION'
            if require_live_scheduler
            else 'OFFLINE_REPORT'
        ),
        'schedule_state_count': len(schedule_state),
        'recent_ingestion': recent_ingestion,
        'database': database,
        'cache': cache,
    }


def repair_release_integrity(db) -> dict[str, int]:
    repaired = {
        'raw_links': 0,
        'offer_variant_links': 0,
        'archived_invalid_prices': 0,
        'archived_duplicate_offers': 0,
        'product_counters': 0,
    }

    # MATCHED durumunda global bağlantısı eksik olan ham kayıtlar tekrar kuyruğa alınır.
    rows = (
        db.query(RawProduct)
        .filter(
            RawProduct.reconciliation_status == 'MATCHED',
            RawProduct.global_product_id.is_(None),
        )
        .all()
    )
    for row in rows:
        row.reconciliation_status = 'PENDING'
        row.reconciliation_error = 'v10 integrity repair: global bağlantı eksikti.'
        repaired['raw_links'] += 1

    # Teklif varyantı başka global ürüne aitse varyant bağlantısı kaldırılır.
    offers = (
        db.query(GlobalOffer, GlobalProductVariant)
        .join(
            GlobalProductVariant,
            GlobalProductVariant.id == GlobalOffer.global_variant_id,
        )
        .filter(
            GlobalOffer.global_product_id
            != GlobalProductVariant.global_product_id
        )
        .all()
    )
    for offer, _variant in offers:
        offer.global_variant_id = None
        repaired['offer_variant_links'] += 1

    for offer in db.query(GlobalOffer).filter(GlobalOffer.current_price <= 0).all():
        offer.is_active = False
        offer.is_hidden = True
        offer.lifecycle_status = 'ARCHIVED'
        offer.duplicate_reason = 'v10 integrity repair: geçersiz fiyat.'
        repaired['archived_invalid_prices'] += 1

    duplicate_groups = (
        db.query(
            GlobalOffer.global_product_id,
            GlobalOffer.store_code,
        )
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == 'ACTIVE',
        )
        .group_by(
            GlobalOffer.global_product_id,
            GlobalOffer.store_code,
        )
        .having(func.count(GlobalOffer.id) > 1)
        .all()
    )
    for product_id, store_code in duplicate_groups:
        offers = (
            db.query(GlobalOffer)
            .filter(
                GlobalOffer.global_product_id == product_id,
                GlobalOffer.store_code == store_code,
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
                GlobalOffer.lifecycle_status == 'ACTIVE',
            )
            .all()
        )
        winner = min(
            offers,
            key=lambda item: (
                float(item.current_price or 0)
                + float(item.shipping_price or 0),
                item.id,
            ),
        )
        for item in offers:
            if item.id == winner.id:
                continue
            item.is_active = False
            item.is_hidden = True
            item.lifecycle_status = 'ARCHIVED'
            item.duplicate_reason = 'v10 integrity repair: aynı mağaza tekrarı.'
            repaired['archived_duplicate_offers'] += 1

    raw_counts = dict(
        db.query(RawProduct.global_product_id, func.count(RawProduct.id))
        .filter(RawProduct.global_product_id.is_not(None))
        .group_by(RawProduct.global_product_id)
        .all()
    )
    offer_counts = dict(
        db.query(GlobalOffer.global_product_id, func.count(GlobalOffer.id))
        .filter(
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == 'ACTIVE',
            GlobalOffer.current_price > 0,
        )
        .group_by(GlobalOffer.global_product_id)
        .all()
    )
    for product in db.query(GlobalProduct).all():
        raw_count = int(raw_counts.get(product.id, 0))
        offer_count = int(offer_counts.get(product.id, 0))
        if (
            int(product.raw_product_count or 0) != raw_count
            or int(product.active_offer_count or 0) != offer_count
        ):
            product.raw_product_count = raw_count
            product.active_offer_count = offer_count
            product.updated_at = datetime.utcnow()
            repaired['product_counters'] += 1

    db.commit()
    invalidate_global_catalog_cache()
    return repaired
