from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, ProductOffer, Store
from app.services.catalog_reconciliation_service import _refresh_global_product_offer_count

ENGINE = "FIRSATAI_STORE_OFFER_RELIABILITY"
VERSION = "22.6.0"


def _total(offer: GlobalOffer) -> float:
    return float(offer.current_price or 0) + float(offer.shipping_price or 0)


def _active_global_offers(db, global_product_id: int) -> list[GlobalOffer]:
    return (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.global_product_id == int(global_product_id),
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == "ACTIVE",
        )
        .order_by(GlobalOffer.store_code.asc(), GlobalOffer.current_price.asc(), GlobalOffer.id.asc())
        .all()
    )


def _legacy_offer_snapshot(db, global_offers: list[GlobalOffer]) -> dict[str, Any]:
    legacy_ids = sorted({
        int(item.legacy_offer_id)
        for item in global_offers
        if item.legacy_offer_id is not None
    })
    if not legacy_ids:
        return {
            "linked_legacy_offer_count": 0,
            "active_legacy_offer_count": 0,
            "archived_legacy_offer_count": 0,
            "note": "Legacy ProductOffer servis kaynağı değildir; GlobalOffer esas alınır.",
        }

    rows = db.query(ProductOffer).filter(ProductOffer.id.in_(legacy_ids)).all()
    active = [
        row for row in rows
        if bool(row.is_active)
        and not bool(row.is_hidden)
        and str(row.lifecycle_status or "").upper() == "ACTIVE"
    ]
    archived = [
        row for row in rows
        if str(row.lifecycle_status or "").upper() == "ARCHIVED"
        or bool(row.is_hidden)
        or not bool(row.is_active)
    ]
    return {
        "linked_legacy_offer_count": len(rows),
        "active_legacy_offer_count": len(active),
        "archived_legacy_offer_count": len(archived),
        "note": (
            "Legacy ProductOffer sayacı kullanıcıya servis edilen mağaza sayısı değildir. "
            "Servis kaynağı GlobalOffer'dır."
        ),
    }


def product_offer_reliability_status(db, global_product_id: int) -> dict[str, Any]:
    product = db.get(GlobalProduct, int(global_product_id))
    if product is None:
        raise ValueError("GlobalProduct bulunamadı.")

    all_rows = (
        db.query(GlobalOffer)
        .filter(GlobalOffer.global_product_id == int(global_product_id))
        .order_by(GlobalOffer.store_code.asc(), GlobalOffer.current_price.asc(), GlobalOffer.id.asc())
        .all()
    )
    active = _active_global_offers(db, global_product_id)

    active_by_store: dict[str, list[GlobalOffer]] = defaultdict(list)
    for offer in active:
        active_by_store[str(offer.store_code or "unknown")].append(offer)

    duplicate_active_stores = {
        store: [int(row.id) for row in rows]
        for store, rows in active_by_store.items()
        if len(rows) > 1
    }

    store_rows = []
    all_by_store: dict[str, list[GlobalOffer]] = defaultdict(list)
    for row in all_rows:
        all_by_store[str(row.store_code or "unknown")].append(row)

    for store_code, rows in sorted(all_by_store.items()):
        active_rows = [
            row for row in rows
            if bool(row.is_active)
            and not bool(row.is_hidden)
            and str(row.lifecycle_status or "").upper() == "ACTIVE"
        ]
        served = min(active_rows, key=_total) if active_rows else None
        store_rows.append({
            "store_code": store_code,
            "global_offer_count": len(rows),
            "active_global_offer_count": len(active_rows),
            "served_offer_id": int(served.id) if served is not None else None,
            "served_price": float(served.current_price) if served is not None else None,
            "lifecycle_statuses": sorted({str(row.lifecycle_status or "") for row in rows}),
        })

    active_store_codes = sorted(active_by_store)
    stored_count = int(product.active_offer_count or 0)
    actual_count = len(active)
    distinct_store_count = len(active_store_codes)

    return {
        "engine": ENGINE,
        "engine_version": VERSION,
        "global_product_id": int(global_product_id),
        "global_product_name": product.canonical_name,
        "serving_source": "GlobalOffer",
        "global_offer_count": len(all_rows),
        "active_global_offer_count": actual_count,
        "active_store_count": distinct_store_count,
        "active_store_codes": active_store_codes,
        "stored_global_product_active_offer_count": stored_count,
        "duplicate_active_store_count": len(duplicate_active_stores),
        "duplicate_active_stores": duplicate_active_stores,
        "count_consistent": stored_count == actual_count,
        "one_active_offer_per_store": not duplicate_active_stores,
        "serving_consistent": (
            stored_count == actual_count
            and not duplicate_active_stores
            and actual_count == distinct_store_count
        ),
        "stores": store_rows,
        "legacy": _legacy_offer_snapshot(db, active),
    }


def audit_product_offer_reliability(db, global_product_id: int) -> dict[str, Any]:
    """GlobalOffer servis katmanını mağaza bazında tekilleştirir.

    MISSING/QUARANTINED/ARCHIVED teklifleri canlandırmaz. Yalnız hâlihazırda
    ACTIVE olan birden fazla aynı-mağaza teklifinden toplam fiyatı en düşük
    olanı aktif bırakır. Farklı mağazalar birbirini hiçbir zaman arşivleyemez.
    """
    product = db.get(GlobalProduct, int(global_product_id))
    if product is None:
        raise ValueError("GlobalProduct bulunamadı.")

    rows = _active_global_offers(db, global_product_id)
    by_store: dict[str, list[GlobalOffer]] = defaultdict(list)
    for row in rows:
        by_store[str(row.store_code or "unknown")].append(row)

    archived_duplicate_count = 0
    changes: list[dict[str, Any]] = []

    for store_code, offers in by_store.items():
        if len(offers) <= 1:
            continue
        winner = min(
            offers,
            key=lambda row: (
                _total(row),
                -(row.last_seen_at or row.updated_at or row.created_at).timestamp(),
                int(row.id),
            ),
        )
        for row in offers:
            if row.id == winner.id:
                continue
            row.is_active = False
            row.is_hidden = True
            row.lifecycle_status = "ARCHIVED"
            row.duplicate_reason = (
                "V22.6 mağaza-içi duplicate: aynı GlobalProduct ve mağazada "
                "daha avantajlı aktif teklif mevcut."
            )
            row.updated_at = datetime.utcnow()
            archived_duplicate_count += 1
            changes.append({
                "store_code": store_code,
                "archived_offer_id": int(row.id),
                "winner_offer_id": int(winner.id),
            })

    _refresh_global_product_offer_count(
        db=db,
        global_product_id=int(global_product_id),
    )
    db.flush()

    status = product_offer_reliability_status(db, global_product_id)
    return {
        "engine": ENGINE,
        "engine_version": VERSION,
        "success": True,
        "archived_duplicate_count": archived_duplicate_count,
        "changes": changes,
        "status": status,
    }


def audit_product_offer_reliability_by_id(global_product_id: int) -> dict[str, Any]:
    db = SessionLocal()
    try:
        result = audit_product_offer_reliability(db, global_product_id)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def status_by_id(global_product_id: int) -> dict[str, Any]:
    db = SessionLocal()
    try:
        return product_offer_reliability_status(db, global_product_id)
    finally:
        db.close()
