from __future__ import annotations

from app.services.production_integrity_guard_v236363_service import (
    ProductionIntegrityGuardV236363,
)

from collections import defaultdict
from datetime import datetime
import hashlib
import json
from typing import Any

from app.database.database import SessionLocal
from app.database.models import (
    GlobalOffer,
    GlobalProduct,
    ProductGroup,
    ProductOffer,
    RawProduct,
)
from app.services.catalog_reconciliation_service import _refresh_global_product_offer_count
from app.services.canonical_identity_convergence_v223_service import (
    _merge_product_groups,
)
from app.services.global_catalog_service import _merge_global_product_into

ENGINE = "FIRSATAI_CANONICAL_ALIAS_RELIABILITY"
VERSION = "23.0.0"


def _canonical_key(identity_source: str) -> str:
    return hashlib.sha256(
        str(identity_source or "").encode("utf-8")
    ).hexdigest()[:32]


def _active_global_offer_count(db, product_id: int) -> int:
    return (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.global_product_id == int(product_id),
            GlobalOffer.is_active.is_(True),
            GlobalOffer.is_hidden.is_(False),
            GlobalOffer.lifecycle_status == "ACTIVE",
        )
        .count()
    )


def _total_global_offer_count(db, product_id: int) -> int:
    return (
        db.query(GlobalOffer)
        .filter(GlobalOffer.global_product_id == int(product_id))
        .count()
    )


def _active_product_offer_count(db, group_id: int) -> int:
    return (
        db.query(ProductOffer)
        .filter(
            ProductOffer.group_id == int(group_id),
            ProductOffer.is_active.is_(True),
            ProductOffer.is_hidden.is_(False),
            ProductOffer.lifecycle_status == "ACTIVE",
        )
        .count()
    )


def converge_exact_identity_aliases(
    db,
    *,
    identity_source: str | None = None,
) -> dict[str, Any]:
    """Aynı canonical identity_source taşıyan duplicate kayıtları tekilleştirir.

    Hash/key geçmiş sürümlerde değişmiş olsa bile identity_source fiziksel ürün
    kimliğinin açık sözleşmesidir. Farklı identity_source kayıtları ASLA merge edilmez.
    """
    global_query = db.query(GlobalProduct).filter(GlobalProduct.status == "ACTIVE")
    if identity_source:
        global_query = global_query.filter(GlobalProduct.identity_source == identity_source)
    globals_all = global_query.all()

    global_buckets: dict[str, list[GlobalProduct]] = defaultdict(list)
    for row in globals_all:
        source = str(row.identity_source or "").strip()
        if source:
            global_buckets[source].append(row)

    merged_global_ids: list[int] = []
    target_by_source: dict[str, int] = {}

    for source, rows in global_buckets.items():
        canonical = _canonical_key(source)
        canonical_rows = [row for row in rows if str(row.identity_key or "") == canonical]
        if canonical_rows:
            # V23.0: canonical key'i zaten taşıyan ID kalıcı winner'dır.
            target = min(canonical_rows, key=lambda row: int(row.id))
        else:
            # İlk canonicalizasyon sırasında en eski ID'yi koru; teklif sayısı ID değiştirmez.
            target = min(rows, key=lambda row: int(row.id))
        rows = [target] + [row for row in rows if row.id != target.id]
        target_by_source[source] = int(target.id)

        for duplicate in rows[1:]:
            duplicate.identity_key = f"alias-merged:{duplicate.id}:{duplicate.identity_key}"[:250]
            db.flush()
            _merge_global_product_into(db, source=duplicate, target=target)
            merged_global_ids.append(int(duplicate.id))
            db.flush()

        # V22.8: Alias merge sonrası kazanan kaydın key'i mutlaka mevcut
        # identity_source'un güncel hash'i olmalı. Aksi halde sonraki ingestion
        # aynı physical ürün için yeni GlobalProduct oluşturabilir.
        canonical_key = _canonical_key(source)
        key_owner = (
            db.query(GlobalProduct)
            .filter(GlobalProduct.identity_key == canonical_key)
            .first()
        )
        if key_owner is not None and int(key_owner.id) != int(target.id):
            # Yalnız aynı identity_source ise güvenli şekilde alias olarak boşalt.
            if str(key_owner.identity_source or "").strip() == source:
                key_owner.identity_key = (
                    f"alias-key-released:{key_owner.id}:{key_owner.identity_key}"
                )[:250]
                db.flush()
            else:
                # Farklı physical identity aynı key'i taşıyorsa sessiz merge yapma.
                raise RuntimeError(
                    "Canonical identity key çakışması: "
                    f"{canonical_key} başka identity_source tarafından kullanılıyor."
                )

        target.identity_key = canonical_key
        target.identity_source = source
        target.updated_at = datetime.utcnow()
        db.flush()

        # Taşınan raw kayıtları hedef canonical key/source ile aynılaştır.
        for raw in (
            db.query(RawProduct)
            .filter(RawProduct.global_product_id == target.id)
            .all()
        ):
            raw.identity_key = target.identity_key
            if raw.identity_payload:
                try:
                    payload = json.loads(raw.identity_payload)
                    if isinstance(payload, dict):
                        payload["identity_key"] = target.identity_key
                        payload["identity_source"] = target.identity_source
                        raw.identity_payload = json.dumps(
                            payload, ensure_ascii=False, default=str
                        )
                except Exception:
                    pass
            raw.updated_at = datetime.utcnow()

        _refresh_global_product_offer_count(db=db, global_product_id=int(target.id))

    # Stale sayaçları global ölçekte temizle: stored count her zaman gerçek ACTIVE
    # GlobalOffer satır sayısından türetilir.
    stale_count_fixed = 0
    products_for_count = db.query(GlobalProduct).all()
    for product in products_for_count:
        actual = _active_global_offer_count(db, product.id)
        if int(product.active_offer_count or 0) != int(actual):
            product.active_offer_count = int(actual)
            product.updated_at = datetime.utcnow()
            stale_count_fixed += 1

    group_query = db.query(ProductGroup)
    if identity_source:
        group_query = group_query.filter(ProductGroup.identity_source == identity_source)
    groups_all = group_query.all()
    group_buckets: dict[str, list[ProductGroup]] = defaultdict(list)
    for row in groups_all:
        source = str(row.identity_source or "").strip()
        if source:
            group_buckets[source].append(row)

    merged_group_ids: list[int] = []
    target_group_by_source: dict[str, int] = {}
    for source, rows in group_buckets.items():
        canonical = _canonical_key(source)
        canonical_rows = [row for row in rows if str(row.group_key or "") == canonical]
        if canonical_rows:
            target = min(canonical_rows, key=lambda row: int(row.id))
        else:
            target = min(rows, key=lambda row: int(row.id))
        rows = [target] + [row for row in rows if row.id != target.id]
        target_group_by_source[source] = int(target.id)

        for duplicate in rows[1:]:
            duplicate.group_key = f"alias-merged:{duplicate.id}:{duplicate.group_key}"[:255]
            db.flush()
            _merge_product_groups(db, duplicate, target)
            merged_group_ids.append(int(duplicate.id))
            db.flush()

        canonical_key = _canonical_key(source)
        key_owner = (
            db.query(ProductGroup)
            .filter(ProductGroup.group_key == canonical_key)
            .first()
        )
        if key_owner is not None and int(key_owner.id) != int(target.id):
            if str(key_owner.identity_source or "").strip() == source:
                key_owner.group_key = (
                    f"alias-key-released:{key_owner.id}:{key_owner.group_key}"
                )[:255]
                db.flush()
            else:
                raise RuntimeError(
                    "Canonical ProductGroup key çakışması: "
                    f"{canonical_key} başka identity_source tarafından kullanılıyor."
                )

        target.group_key = canonical_key
        target.identity_source = source
        target.updated_at = datetime.utcnow()
        db.flush()

    db.flush()
    return {
        "engine": ENGINE,
        "engine_version": VERSION,
        "success": True,
        "identity_source": identity_source,
        "merged_global_product_ids": merged_global_ids,
        "merged_product_group_ids": merged_group_ids,
        "stale_active_offer_count_fixed": stale_count_fixed,
        "canonical_key_stabilized": True,
        "target_global_product_id": (
            target_by_source.get(identity_source) if identity_source else None
        ),
        "target_product_group_id": (
            target_group_by_source.get(identity_source) if identity_source else None
        ),
    }


def converge_exact_identity_aliases_by_source(identity_source: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        result = converge_exact_identity_aliases(
            db,
            identity_source=str(identity_source or "").strip(),
        )
        ProductionIntegrityGuardV236363.assert_clean(
            db,
            context="v236366_canonical_alias_reliability",
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def audit_all_aliases() -> dict[str, Any]:
    db = SessionLocal()
    try:
        result = converge_exact_identity_aliases(db)
        ProductionIntegrityGuardV236363.assert_clean(
            db,
            context="v236366_canonical_alias_reliability",
        )
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
