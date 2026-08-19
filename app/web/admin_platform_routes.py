from __future__ import annotations

from collections import Counter, defaultdict
from difflib import SequenceMatcher
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from app.database.database import SessionLocal
from app.database.models import (
    Favorite,
    NotificationDelivery,
    OfferPriceHistory,
    PriceAlert,
    PriceHistory,
    ProductDB,
    ProductFeature,
    ProductFeatureValue,
    ProductGroup,
    ProductOffer,
    ProductReview,
    ReviewVote,
    Store,
    UserAccount,
    UserNotification,
)

from app.services.offer_maintenance_service import (
    offer_health_summary,
    run_offer_maintenance,
)

from app.services.offer_validation_service import build_validation_report
from app.services.offer_health_dashboard_service import build_offer_health_dashboard

router = APIRouter(prefix='/admin', tags=['Admin Platform'])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))


def _safe_count(session, model) -> int:
    try:
        return int(session.query(func.count(model.id)).scalar() or 0)
    except SQLAlchemyError:
        session.rollback()
        return 0


def _fmt_money(value: Any) -> str:
    try:
        return f"{float(value or 0):,.2f} TL".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return '0,00 TL'


def _base_stats(session) -> dict[str, int]:
    return {
        'products': _safe_count(session, ProductDB),
        'groups': _safe_count(session, ProductGroup),
        'offers': _safe_count(session, ProductOffer),
        'stores': _safe_count(session, Store),
        'features': _safe_count(session, ProductFeature),
        'users': _safe_count(session, UserAccount),
        'reviews': _safe_count(session, ProductReview),
        'alerts': _safe_count(session, PriceAlert),
    }


@router.get('/catalog', response_class=HTMLResponse)
def catalog_center(request: Request):
    with SessionLocal() as session:
        stats = _base_stats(session)
        missing_image = session.query(ProductDB).filter(or_(ProductDB.image.is_(None), ProductDB.image == '')).count()
        missing_specs = session.query(ProductDB).filter(or_(ProductDB.specifications.is_(None), ProductDB.specifications == '')).count()
        missing_brand = session.query(ProductDB).filter(or_(ProductDB.brand.is_(None), ProductDB.brand == '')).count()
        recent = session.query(ProductDB).order_by(ProductDB.updated_at.desc()).limit(8).all()
        categories = session.query(ProductDB.category, func.count(ProductDB.id)).group_by(ProductDB.category).order_by(func.count(ProductDB.id).desc()).limit(8).all()
    return templates.TemplateResponse(request=request, name='admin_catalog_center.html', context={
        'stats': stats,
        'quality': {'missing_image': missing_image, 'missing_specs': missing_specs, 'missing_brand': missing_brand},
        'recent': recent,
        'categories': categories,
        'fmt_money': _fmt_money,
    })


@router.get('/stores', response_class=HTMLResponse)
def stores_center(request: Request, q: str = Query(default='')):
    with SessionLocal() as session:
        query = session.query(Store)
        if q:
            query = query.filter(or_(Store.name.ilike(f'%{q}%'), Store.code.ilike(f'%{q}%')))
        stores = query.order_by(Store.is_active.desc(), Store.name.asc()).all()
        offer_counts = dict(session.query(ProductOffer.store_id, func.count(ProductOffer.id)).group_by(ProductOffer.store_id).all())
        best_counts = dict(session.query(ProductOffer.store_id, func.count(ProductOffer.id)).filter(ProductOffer.is_best_offer.is_(True)).group_by(ProductOffer.store_id).all())
        avg_prices = dict(session.query(ProductOffer.store_id, func.avg(ProductOffer.current_price)).group_by(ProductOffer.store_id).all())
    return templates.TemplateResponse(request=request, name='admin_stores.html', context={
        'stores': stores, 'offer_counts': offer_counts, 'best_counts': best_counts, 'avg_prices': avg_prices,
        'q': q, 'fmt_money': _fmt_money,
    })


@router.get('/offer-health', response_class=HTMLResponse)
def offer_health_center(
    request: Request,
    store: str = Query(default=''),
):
    with SessionLocal() as session:
        dashboard = build_offer_health_dashboard(session, selected_store=store)
        stores = session.query(Store).order_by(Store.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name='admin_offer_health.html',
        context={
            'dashboard': dashboard,
            'stores': stores,
            'selected_store': store,
        },
    )


@router.get('/offer-validation', response_class=HTMLResponse)
def offer_validation_center(
    request: Request,
    store: str = Query(default=''),
):
    with SessionLocal() as session:
        report = build_validation_report(session, selected_store=store)
        stores = session.query(Store).order_by(Store.name.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name='admin_offer_validation.html',
        context={
            'report': report,
            'stores': stores,
            'selected_store': store,
            'fmt_money': _fmt_money,
        },
    )


@router.get('/offers', response_class=HTMLResponse)
def offers_center(
    request: Request,
    q: str = Query(default=''),
    store: int | None = Query(default=None),
    status: str = Query(default=''),
    visibility: str = Query(default='active'),
    price_flag: str = Query(default=''),
    lifecycle: str = Query(default=''),
):
    with SessionLocal() as session:
        query = (
            session.query(ProductOffer, ProductDB, Store, ProductGroup)
            .join(ProductDB, ProductDB.id == ProductOffer.product_id)
            .join(Store, Store.id == ProductOffer.store_id)
            .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        )
        if q:
            query = query.filter(or_(
                ProductDB.name.ilike(f'%{q}%'),
                ProductGroup.canonical_name.ilike(f'%{q}%'),
                ProductOffer.seller.ilike(f'%{q}%'),
                ProductOffer.store_product_id.ilike(f'%{q}%'),
            ))
        if store:
            query = query.filter(ProductOffer.store_id == store)
        if status == 'in_stock':
            query = query.filter(ProductOffer.availability.ilike('%stok%')).filter(~ProductOffer.availability.ilike('%yok%'))
        elif status == 'out_of_stock':
            query = query.filter(or_(ProductOffer.availability.ilike('%yok%'), ProductOffer.availability.ilike('%tükendi%')))
        elif status:
            query = query.filter(ProductOffer.availability.ilike(f'%{status}%'))
        if visibility == 'active':
            query = query.filter(ProductOffer.is_hidden.is_(False))
        elif visibility == 'hidden':
            query = query.filter(ProductOffer.is_hidden.is_(True))
        if lifecycle:
            query = query.filter(ProductOffer.lifecycle_status == lifecycle.upper())

        raw_rows = query.order_by(ProductOffer.updated_at.desc()).limit(400).all()
        group_ids = {offer.group_id for offer, _, _, _ in raw_rows}
        group_prices: dict[int, list[float]] = defaultdict(list)
        if group_ids:
            for gid, price in (
                session.query(ProductOffer.group_id, ProductOffer.current_price)
                .filter(ProductOffer.group_id.in_(group_ids), ProductOffer.is_hidden.is_(False))
                .all()
            ):
                if price and float(price) > 0:
                    group_prices[int(gid)].append(float(price))

        rows = []
        suspicious_count = 0
        for offer, product, store_obj, group in raw_rows:
            prices = sorted(group_prices.get(offer.group_id, []))
            median = prices[len(prices)//2] if prices else float(offer.current_price or 0)
            current = float(offer.current_price or 0)
            suspicious = current <= 0 or (median > 0 and (current < median * 0.45 or current > median * 2.20))
            if suspicious:
                suspicious_count += 1
            if price_flag == 'suspicious' and not suspicious:
                continue
            if price_flag == 'best' and not offer.is_best_offer:
                continue
            diff_percent = 0.0
            if median > 0:
                diff_percent = ((current - median) / median) * 100
            rows.append({
                'offer': offer,
                'product': product,
                'store': store_obj,
                'group': group,
                'median_price': median,
                'difference_percent': diff_percent,
                'suspicious': suspicious,
            })

        stores = session.query(Store).order_by(Store.name.asc()).all()
        stats = {
            'total': _safe_count(session, ProductOffer),
            'best': session.query(ProductOffer).filter(ProductOffer.is_best_offer.is_(True), ProductOffer.is_hidden.is_(False)).count(),
            'available': session.query(ProductOffer).filter(ProductOffer.availability.ilike('%stok%'), ProductOffer.is_hidden.is_(False)).count(),
            'hidden': session.query(ProductOffer).filter(ProductOffer.is_hidden.is_(True)).count(),
            'suspicious': suspicious_count,
        }
        health = offer_health_summary(session)
    return templates.TemplateResponse(request=request, name='admin_offers.html', context={
        'rows': rows,
        'stores': stores,
        'stats': stats,
        'q': q,
        'selected_store': store,
        'status': status,
        'visibility': visibility,
        'price_flag': price_flag,
        'lifecycle': lifecycle,
        'health': health,
        'fmt_money': _fmt_money,
    })


def _refresh_best_offer(session, group_id: int) -> None:
    offers = session.query(ProductOffer).filter(ProductOffer.group_id == group_id).all()
    for item in offers:
        item.is_best_offer = False
    eligible = [
        item for item in offers
        if not item.is_hidden
        and float(item.current_price or 0) > 0
        and 'yok' not in str(item.availability or '').lower()
        and 'tükendi' not in str(item.availability or '').lower()
    ]
    if eligible:
        min(eligible, key=lambda item: float(item.current_price)).is_best_offer = True


@router.post('/offers/maintenance')
def offer_maintenance(action: str = Form(default='full')):
    with SessionLocal() as session:
        result = run_offer_maintenance(session, action=action)
        session.commit()
    values = result.to_dict()
    message = (
        f"Kontrol {values['checked']}; tekrar {values['duplicates_archived']}; "
        f"kayıp {values['marked_missing']}; arşiv {values['archived_stale']}; "
        f"en iyi fiyat grubu {values['best_offer_groups_fixed']}"
    )
    return RedirectResponse(
        f"/admin/offers?maintenance_message={message}",
        status_code=303,
    )


@router.post('/offers/bulk-action')
def offer_bulk_action(
    action: str = Form(...),
    selected_ids: list[int] = Form(default=[]),
):
    if not selected_ids:
        return RedirectResponse('/admin/offers', status_code=303)
    with SessionLocal() as session:
        offers = session.query(ProductOffer).filter(ProductOffer.id.in_(selected_ids)).all()
        group_ids = {item.group_id for item in offers}
        if action == 'delete':
            for item in offers:
                session.query(OfferPriceHistory).filter(OfferPriceHistory.offer_id == item.id).delete(synchronize_session=False)
                session.delete(item)
        elif action == 'hide':
            for item in offers:
                item.is_hidden = True
                item.is_best_offer = False
        elif action == 'show':
            for item in offers:
                item.is_hidden = False
        elif action == 'out_of_stock':
            for item in offers:
                item.availability = 'Stokta Yok'
                item.is_best_offer = False
        elif action == 'in_stock':
            for item in offers:
                item.availability = 'Stokta'
        for gid in group_ids:
            _refresh_best_offer(session, gid)
        session.commit()
    return RedirectResponse('/admin/offers', status_code=303)


@router.post('/offers/{offer_id}/toggle-visibility')
def toggle_offer_visibility(offer_id: int):
    with SessionLocal() as session:
        offer = session.query(ProductOffer).filter(ProductOffer.id == offer_id).first()
        if offer:
            offer.is_hidden = not bool(offer.is_hidden)
            group_id = offer.group_id
            _refresh_best_offer(session, group_id)
            session.commit()
    return RedirectResponse('/admin/offers', status_code=303)


@router.post('/offers/{offer_id}/toggle-stock')
def toggle_offer_stock(offer_id: int):
    with SessionLocal() as session:
        offer = session.query(ProductOffer).filter(ProductOffer.id == offer_id).first()
        if offer:
            lower = str(offer.availability or '').lower()
            offer.availability = 'Stokta' if ('yok' in lower or 'tükendi' in lower) else 'Stokta Yok'
            _refresh_best_offer(session, offer.group_id)
            session.commit()
    return RedirectResponse('/admin/offers', status_code=303)


@router.post('/offers/{offer_id}/delete')
def delete_offer(offer_id: int):
    with SessionLocal() as session:
        offer = session.query(ProductOffer).filter(ProductOffer.id == offer_id).first()
        if offer:
            group_id = offer.group_id
            session.query(OfferPriceHistory).filter(OfferPriceHistory.offer_id == offer.id).delete(synchronize_session=False)
            session.delete(offer)
            session.flush()
            _refresh_best_offer(session, group_id)
            session.commit()
    return RedirectResponse('/admin/offers', status_code=303)


def _matching_normalize(value: Any) -> str:
    text = str(value or '').casefold().translate(str.maketrans({
        'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c',
    }))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text).split())


def _matching_tokens(group: ProductGroup) -> set[str]:
    return set(_matching_normalize(' '.join(filter(None, [
        group.brand, group.model, group.canonical_name, group.category,
    ]))).split())


def _matching_score(left: ProductGroup, right: ProductGroup) -> tuple[int, list[str]]:
    reasons: list[str] = []
    left_brand = _matching_normalize(left.brand)
    right_brand = _matching_normalize(right.brand)
    if left_brand and right_brand and left_brand != right_brand:
        return 0, ['Markalar farklı']

    left_name = _matching_normalize(left.canonical_name)
    right_name = _matching_normalize(right.canonical_name)
    name_ratio = SequenceMatcher(None, left_name, right_name).ratio()
    token_union = _matching_tokens(left) | _matching_tokens(right)
    token_intersection = _matching_tokens(left) & _matching_tokens(right)
    token_ratio = len(token_intersection) / max(1, len(token_union))
    score = int(round((name_ratio * 58 + token_ratio * 42) * 100 / 100))

    if left_brand and left_brand == right_brand:
        score += 10
        reasons.append('Aynı marka')
    left_model = _matching_normalize(left.model)
    right_model = _matching_normalize(right.model)
    if left_model and right_model:
        if left_model == right_model:
            score += 24
            reasons.append('Model aynı')
        elif left_model in right_model or right_model in left_model:
            score += 12
            reasons.append('Model ailesi benzer')
    left_category = _matching_normalize(left.category)
    right_category = _matching_normalize(right.category)
    if left_category and right_category:
        if left_category == right_category:
            score += 6
            reasons.append('Kategori aynı')
        else:
            score -= 18
            reasons.append('Kategori farklı')
    if name_ratio >= .88:
        reasons.append('Ürün adı çok benzer')
    elif token_ratio >= .55:
        reasons.append('Ortak teknik ifadeler')
    return max(0, min(100, score)), reasons or ['İsim benzerliği']


def _matching_refresh_group(session, group_id: int) -> None:
    group = session.query(ProductGroup).filter(ProductGroup.id == group_id).first()
    if not group:
        return
    rows = (
        session.query(ProductOffer, ProductDB)
        .join(ProductDB, ProductDB.id == ProductOffer.product_id)
        .filter(ProductOffer.group_id == group_id)
        .order_by(ProductOffer.is_best_offer.desc(), ProductOffer.updated_at.desc())
        .all()
    )
    if not rows:
        return
    _, product = rows[0]
    group.canonical_name = product.name or group.canonical_name
    group.normalized_name = _matching_normalize(product.name)
    group.brand = product.brand or group.brand
    group.model = product.model or group.model
    group.category = product.category or group.category
    group.image = product.image or group.image
    group.updated_at = datetime.utcnow()
    _refresh_best_offer(session, group_id)


@router.get('/matching', response_class=HTMLResponse)
def matching_center(
    request: Request,
    q: str = Query(default=''),
    quality: str = Query(default=''),
    selected_group: int | None = Query(default=None),
):
    with SessionLocal() as session:
        offer_counts_sq = (
            session.query(
                ProductOffer.group_id.label('gid'),
                func.count(ProductOffer.id).label('offer_count'),
            )
            .group_by(ProductOffer.group_id)
            .subquery()
        )
        query = (
            session.query(ProductGroup, func.coalesce(offer_counts_sq.c.offer_count, 0))
            .join(offer_counts_sq, offer_counts_sq.c.gid == ProductGroup.id)
            .filter(func.coalesce(offer_counts_sq.c.offer_count, 0) > 0)
        )
        if q:
            query = query.filter(or_(
                ProductGroup.canonical_name.ilike(f'%{q}%'),
                ProductGroup.brand.ilike(f'%{q}%'),
                ProductGroup.model.ilike(f'%{q}%'),
                ProductGroup.category.ilike(f'%{q}%'),
            ))
        if quality == 'single':
            query = query.filter(func.coalesce(offer_counts_sq.c.offer_count, 0) <= 1)
        elif quality == 'multi':
            query = query.filter(func.coalesce(offer_counts_sq.c.offer_count, 0) >= 2)
        rows_raw = query.order_by(
            func.coalesce(offer_counts_sq.c.offer_count, 0).asc(),
            ProductGroup.updated_at.desc(),
        ).limit(250).all()

        group_ids = [group.id for group, _ in rows_raw]
        offer_rows = []
        if group_ids:
            offer_rows = (
                session.query(ProductOffer, ProductDB, Store)
                .join(ProductDB, ProductDB.id == ProductOffer.product_id)
                .join(Store, Store.id == ProductOffer.store_id)
                .filter(ProductOffer.group_id.in_(group_ids))
                .order_by(ProductOffer.current_price.asc())
                .all()
            )
        grouped_offers: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for offer, product, store in offer_rows:
            grouped_offers[int(offer.group_id)].append({
                'offer': offer, 'product': product, 'store': store,
            })

        rows = []
        for group, offer_count in rows_raw:
            offers = grouped_offers.get(group.id, [])
            stores = {item['store'].id for item in offers}
            product_names = {_matching_normalize(item['product'].name) for item in offers}
            conflict = len(product_names) > 1 and len(stores) != len(offers)
            rows.append({
                'group': group,
                'offer_count': int(offer_count or 0),
                'store_count': len(stores),
                'offers': offers,
                'conflict': conflict,
            })

        if quality == 'conflict':
            rows = [row for row in rows if row['conflict']]

        selected = next((row for row in rows if row['group'].id == selected_group), None)
        if selected_group and selected is None:
            group = session.query(ProductGroup).filter(ProductGroup.id == selected_group).first()
            if group:
                offers = grouped_offers.get(group.id)
                if offers is None:
                    offers = []
                    for offer, product, store in (
                        session.query(ProductOffer, ProductDB, Store)
                        .join(ProductDB, ProductDB.id == ProductOffer.product_id)
                        .join(Store, Store.id == ProductOffer.store_id)
                        .filter(ProductOffer.group_id == group.id)
                        .all()
                    ):
                        offers.append({'offer': offer, 'product': product, 'store': store})
                selected = {'group': group, 'offer_count': len(offers), 'store_count': len({x['store'].id for x in offers}), 'offers': offers, 'conflict': False}

        all_groups = session.query(ProductGroup).order_by(ProductGroup.updated_at.desc()).limit(500).all()
        suggestions: list[dict[str, Any]] = []
        source_groups = [selected['group']] if selected else [row['group'] for row in rows if row['offer_count'] <= 1][:80]
        for left in source_groups:
            scored = []
            for right in all_groups:
                if left.id == right.id:
                    continue
                score, reasons = _matching_score(left, right)
                if score >= 62:
                    scored.append({'source': left, 'candidate': right, 'score': score, 'reasons': reasons})
            scored.sort(key=lambda item: item['score'], reverse=True)
            suggestions.extend(scored[:5 if selected else 1])
        suggestions.sort(key=lambda item: item['score'], reverse=True)
        suggestions = suggestions[:30]

        total_groups = int(
            session.query(func.count())
            .select_from(offer_counts_sq)
            .filter(offer_counts_sq.c.offer_count > 0)
            .scalar() or 0
        )
        multi_groups = int(session.query(func.count()).select_from(offer_counts_sq).filter(offer_counts_sq.c.offer_count >= 2).scalar() or 0)
        single_groups = max(0, total_groups - multi_groups)
        conflict_groups = sum(1 for row in rows if row['conflict'])

    return templates.TemplateResponse(request=request, name='admin_matching_pro.html', context={
        'rows': rows,
        'q': q,
        'quality': quality,
        'selected': selected,
        'selected_group': selected_group,
        'suggestions': suggestions,
        'target_groups': all_groups,
        'stats': {
            'total': total_groups,
            'multi': multi_groups,
            'single': single_groups,
            'conflict': conflict_groups,
            'suggestions': len(suggestions),
        },
        'fmt_money': _fmt_money,
    })


@router.post('/matching/merge')
def matching_merge(
    source_group_ids: list[int] = Form(default=[]),
    target_group_id: int = Form(...),
):
    source_ids = {int(value) for value in source_group_ids if int(value) != int(target_group_id)}
    with SessionLocal() as session:
        target = session.query(ProductGroup).filter(ProductGroup.id == target_group_id).first()
        if target and source_ids:
            session.query(ProductOffer).filter(ProductOffer.group_id.in_(source_ids)).update(
                {ProductOffer.group_id: target_group_id}, synchronize_session=False,
            )
            for source in session.query(ProductGroup).filter(ProductGroup.id.in_(source_ids)).all():
                session.delete(source)
            _matching_refresh_group(session, target_group_id)
            session.commit()
    return RedirectResponse(f'/admin/matching?selected_group={target_group_id}', status_code=303)


@router.post('/matching/move-offers')
def matching_move_offers(
    offer_ids: list[int] = Form(default=[]),
    target_group_id: int = Form(...),
):
    with SessionLocal() as session:
        offers = session.query(ProductOffer).filter(ProductOffer.id.in_(offer_ids)).all() if offer_ids else []
        old_group_ids = {offer.group_id for offer in offers}
        if session.query(ProductGroup).filter(ProductGroup.id == target_group_id).first():
            for offer in offers:
                offer.group_id = target_group_id
            for gid in old_group_ids | {target_group_id}:
                _matching_refresh_group(session, gid)
            for gid in old_group_ids:
                if not session.query(ProductOffer.id).filter(ProductOffer.group_id == gid).first():
                    empty = session.query(ProductGroup).filter(ProductGroup.id == gid).first()
                    if empty:
                        session.delete(empty)
            session.commit()
    return RedirectResponse(f'/admin/matching?selected_group={target_group_id}', status_code=303)


@router.post('/matching/split')
def matching_split(
    offer_ids: list[int] = Form(default=[]),
    new_name: str = Form(default=''),
):
    if not offer_ids:
        return RedirectResponse('/admin/matching', status_code=303)
    with SessionLocal() as session:
        offers = session.query(ProductOffer).filter(ProductOffer.id.in_(offer_ids)).all()
        if not offers:
            return RedirectResponse('/admin/matching', status_code=303)
        old_group_ids = {offer.group_id for offer in offers}
        first_product = session.query(ProductDB).filter(ProductDB.id == offers[0].product_id).first()
        seed = f"manual:{datetime.utcnow().isoformat()}:{','.join(map(str, sorted(offer_ids)))}"
        new_group = ProductGroup(
            group_key=hashlib.sha256(seed.encode('utf-8')).hexdigest()[:32],
            identity_source='manual_split',
            canonical_name=(new_name.strip() or (first_product.name if first_product else 'Yeni ürün grubu')),
            normalized_name=_matching_normalize(new_name.strip() or (first_product.name if first_product else 'yeni urun grubu')),
            brand=first_product.brand if first_product else None,
            model=first_product.model if first_product else None,
            category=first_product.category if first_product else None,
            image=first_product.image if first_product else None,
        )
        session.add(new_group)
        session.flush()
        for offer in offers:
            offer.group_id = new_group.id
        _matching_refresh_group(session, new_group.id)
        for gid in old_group_ids:
            _matching_refresh_group(session, gid)
        session.commit()
        new_id = new_group.id
    return RedirectResponse(f'/admin/matching?selected_group={new_id}', status_code=303)


@router.get('/brands', response_class=HTMLResponse)
def brands_center(request: Request, q: str = Query(default='')):
    with SessionLocal() as session:
        query = session.query(ProductDB.brand, func.count(ProductDB.id), func.avg(ProductDB.price), func.avg(ProductDB.ai_score)).filter(ProductDB.brand.is_not(None), ProductDB.brand != '').group_by(ProductDB.brand)
        if q:
            query = query.filter(ProductDB.brand.ilike(f'%{q}%'))
        rows = query.order_by(func.count(ProductDB.id).desc()).limit(200).all()
    return templates.TemplateResponse(request=request, name='admin_brands.html', context={'rows': rows, 'q': q, 'fmt_money': _fmt_money})


@router.get('/users', response_class=HTMLResponse)
def users_center(request: Request, q: str = Query(default=''), state: str = Query(default='')):
    with SessionLocal() as session:
        query = session.query(UserAccount)
        if q:
            query = query.filter(or_(UserAccount.email.ilike(f'%{q}%'), UserAccount.display_name.ilike(f'%{q}%')))
        if state == 'active':
            query = query.filter(UserAccount.is_active.is_(True))
        elif state == 'passive':
            query = query.filter(UserAccount.is_active.is_(False))
        users = query.order_by(UserAccount.created_at.desc()).limit(200).all()
        review_counts = dict(session.query(ProductReview.user_id, func.count(ProductReview.id)).group_by(ProductReview.user_id).all())
        stats = {'total': _safe_count(session, UserAccount), 'active': session.query(UserAccount).filter(UserAccount.is_active.is_(True)).count(), 'reviews': _safe_count(session, ProductReview), 'alerts': _safe_count(session, PriceAlert)}
    return templates.TemplateResponse(request=request, name='admin_users.html', context={'users': users, 'review_counts': review_counts, 'stats': stats, 'q': q, 'state': state})


@router.get('/reviews', response_class=HTMLResponse)
def reviews_center(request: Request, q: str = Query(default=''), rating: int | None = Query(default=None)):
    with SessionLocal() as session:
        query = session.query(ProductReview, UserAccount, ProductGroup).join(UserAccount, UserAccount.id == ProductReview.user_id).join(ProductGroup, ProductGroup.id == ProductReview.product_group_id)
        if q:
            query = query.filter(or_(ProductReview.title.ilike(f'%{q}%'), ProductReview.body.ilike(f'%{q}%'), ProductGroup.canonical_name.ilike(f'%{q}%')))
        if rating:
            query = query.filter(ProductReview.rating == rating)
        rows = query.order_by(ProductReview.created_at.desc()).limit(150).all()
        avg_rating = session.query(func.avg(ProductReview.rating)).scalar() or 0
        helpful = session.query(func.count(ReviewVote.id)).scalar() or 0
    return templates.TemplateResponse(request=request, name='admin_reviews.html', context={'rows': rows, 'q': q, 'rating': rating, 'stats': {'total': _safe_count(session, ProductReview), 'average': round(float(avg_rating), 1), 'helpful': helpful}})


@router.get('/notifications-admin', response_class=HTMLResponse)
def notifications_admin(request: Request):
    with SessionLocal() as session:
        notifications = session.query(UserNotification, UserAccount).join(UserAccount, UserAccount.id == UserNotification.user_id).order_by(UserNotification.created_at.desc()).limit(120).all()
        deliveries = session.query(NotificationDelivery).order_by(NotificationDelivery.created_at.desc()).limit(120).all()
        status_counts = Counter(str(item.status or 'unknown') for item in deliveries)
        stats = {'notifications': _safe_count(session, UserNotification), 'deliveries': _safe_count(session, NotificationDelivery), 'pending': status_counts.get('pending', 0), 'sent': status_counts.get('sent', 0)}
    return templates.TemplateResponse(request=request, name='admin_notifications.html', context={'notifications': notifications, 'deliveries': deliveries, 'stats': stats})


@router.get('/reports', response_class=HTMLResponse)
def reports_center(request: Request):
    with SessionLocal() as session:
        stats = _base_stats(session)
        category_rows = session.query(ProductDB.category, func.count(ProductDB.id), func.avg(ProductDB.price), func.avg(ProductDB.ai_score)).group_by(ProductDB.category).order_by(func.count(ProductDB.id).desc()).limit(12).all()
        store_rows = session.query(Store.name, func.count(ProductOffer.id), func.avg(ProductOffer.current_price)).outerjoin(ProductOffer, ProductOffer.store_id == Store.id).group_by(Store.id).order_by(func.count(ProductOffer.id).desc()).all()
        cutoff = datetime.utcnow() - timedelta(days=30)
        price_updates = session.query(func.date(PriceHistory.created_at), func.count(PriceHistory.id)).filter(PriceHistory.created_at >= cutoff).group_by(func.date(PriceHistory.created_at)).all()
    return templates.TemplateResponse(request=request, name='admin_reports.html', context={'stats': stats, 'category_rows': category_rows, 'store_rows': store_rows, 'price_updates': price_updates, 'fmt_money': _fmt_money})


@router.get('/settings', response_class=HTMLResponse)
def settings_center(request: Request):
    with SessionLocal() as session:
        stats = _base_stats(session)
    return templates.TemplateResponse(request=request, name='admin_settings.html', context={'stats': stats})
