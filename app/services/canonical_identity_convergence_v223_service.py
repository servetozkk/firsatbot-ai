from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from app.database.database import SessionLocal
from app.database.models import (
    Favorite,
    GlobalOffer,
    GlobalProduct,
    PriceAlert,
    ProductFeatureValue,
    ProductGroup,
    ProductOffer,
    ProductReview,
    RawProduct,
    RecentlyViewed,
)
from app.services.global_catalog_service import _merge_global_product_into


ENGINE = "FIRSATAI_CANONICAL_IDENTITY_CONVERGENCE"
VERSION = "23.13.0"


def _parse_identity_source(value: str | None) -> dict[str, str]:
    text = str(value or "").strip()
    if not text.startswith("identity_v3:"):
        return {}
    result: dict[str, str] = {}
    for chunk in text.split(":", 1)[1].split("|"):
        if "=" not in chunk:
            continue
        key, raw = chunk.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if key and raw:
            result[key] = raw
    return result


def _is_phone_identity(parts: dict[str, str], category: str | None = None) -> bool:
    family = str(parts.get("family") or "").casefold().strip()
    brand = str(parts.get("brand") or "").casefold().strip()
    raw_category = str(category or "")
    cat = raw_category.casefold()
    cat_parts = [
        part.casefold().strip()
        for part in re.split(r"[>›»|]+", raw_category)
        if part.strip()
    ]
    leaf = cat_parts[-1] if cat_parts else cat

    phone_leaf_markers = (
        "cep telefonu", "akıllı telefon", "akilli telefon", "smartphone",
        "android cep telefonu", "ios cep telefonu",
    )
    non_phone_leaf_markers = (
        "tablet", "laptop", "notebook", "dizüstü", "dizustu",
        "akıllı saat", "akilli saat", "smartwatch", "giyilebilir",
        "kulaklık", "kulaklik", "headphone", "earbud", "tws",
        "aksesuar", "şarj", "sarj", "charger", "adapt", "kablo",
        "kılıf", "kilif", "ekran koruyucu", "powerbank",
    )

    if any(marker in leaf for marker in phone_leaf_markers):
        return True
    # V23.13: V22.3 yalnız telefon canonical convergence motorudur.
    # Galaxy Tab/Watch/Buds gibi ailelerin ``galaxy``/marka kalıbı yüzünden
    # telefon sanılıp RAM/variant sözleşmesinin bozulmasını engelle.
    if any(marker in leaf for marker in non_phone_leaf_markers):
        return False

    if family.startswith(
        (
            "iphone ", "redmi ", "poco ", "galaxy ",
            "fold ", "flip ", "xiaomi ",
        )
    ):
        return True
    if brand == "apple" and family.startswith("iphone"):
        return True
    return any(
        marker in cat
        for marker in ("cep telefonu", "akıllı telefon", "akilli telefon", "smartphone")
    )


def canonical_phone_identity_source(
    identity_source: str | None,
    *,
    category: str | None = None,
) -> str | None:
    parts = _parse_identity_source(identity_source)
    if not parts or not _is_phone_identity(parts, category):
        return None

    ordered: list[str] = []
    # V23.4: Explicit marketed network (örn. 5G) phone canonical contract'ın parçasıdır.
    for key in ("brand", "family", "variant", "storage", "network", "screen", "model_code", "product_code"):
        value = parts.get(key)
        if value:
            ordered.append(f"{key}={value}")
    if not ordered:
        return None
    return "identity_v3:" + "|".join(ordered)


def _key(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]


def _merge_simple_fk_rows(db, model, attr: str, source_id: int, target_id: int) -> int:
    rows = db.query(model).filter(getattr(model, attr) == source_id).all()
    moved = 0
    for row in rows:
        setattr(row, attr, target_id)
        moved += 1
    return moved


def _merge_unique_user_rows(
    db,
    model,
    *,
    attr: str,
    source_id: int,
    target_id: int,
    owner_attr: str,
) -> int:
    rows = db.query(model).filter(getattr(model, attr) == source_id).all()
    moved = 0
    for row in rows:
        owner = getattr(row, owner_attr)
        existing = (
            db.query(model)
            .filter(
                getattr(model, attr) == target_id,
                getattr(model, owner_attr) == owner,
            )
            .first()
        )
        if existing is not None:
            db.delete(row)
        else:
            setattr(row, attr, target_id)
            moved += 1
    return moved


def _merge_feature_values(db, source_id: int, target_id: int) -> int:
    rows = (
        db.query(ProductFeatureValue)
        .filter(ProductFeatureValue.product_group_id == source_id)
        .all()
    )
    moved = 0
    for row in rows:
        existing = (
            db.query(ProductFeatureValue)
            .filter(
                ProductFeatureValue.product_group_id == target_id,
                ProductFeatureValue.feature_id == row.feature_id,
            )
            .first()
        )
        if existing is not None:
            # Target değeri dolu değilse source bilgisini kaybetme.
            for field in ("value_text", "value_number", "value_boolean", "raw_value"):
                if hasattr(existing, field) and getattr(existing, field, None) in (None, ""):
                    setattr(existing, field, getattr(row, field, None))
            db.delete(row)
        else:
            row.product_group_id = target_id
            moved += 1
    return moved


def _merge_product_groups(db, source: ProductGroup, target: ProductGroup) -> dict[str, int]:
    if int(source.id) == int(target.id):
        return {}

    counts: dict[str, int] = {}
    counts["product_offers"] = _merge_simple_fk_rows(
        db, ProductOffer, "group_id", source.id, target.id
    )
    counts["feature_values"] = _merge_feature_values(db, source.id, target.id)
    counts["favorites"] = _merge_unique_user_rows(
        db, Favorite,
        attr="product_group_id",
        source_id=source.id,
        target_id=target.id,
        owner_attr="visitor_id",
    )
    counts["price_alerts"] = _merge_unique_user_rows(
        db, PriceAlert,
        attr="product_group_id",
        source_id=source.id,
        target_id=target.id,
        owner_attr="visitor_id",
    )
    counts["recently_viewed"] = _merge_unique_user_rows(
        db, RecentlyViewed,
        attr="product_group_id",
        source_id=source.id,
        target_id=target.id,
        owner_attr="user_id",
    )
    counts["reviews"] = _merge_unique_user_rows(
        db, ProductReview,
        attr="product_group_id",
        source_id=source.id,
        target_id=target.id,
        owner_attr="user_id",
    )

    # Kullanıcıya görünen daha dolu alanları koru.
    if not target.image and source.image:
        target.image = source.image
    if not target.category and source.category:
        target.category = source.category
    if not target.brand and source.brand:
        target.brand = source.brand
    if not target.model and source.model:
        target.model = source.model
    target.updated_at = datetime.utcnow()

    db.delete(source)
    return counts


def _group_offer_count(db, group_id: int) -> int:
    return (
        db.query(ProductOffer)
        .filter(ProductOffer.group_id == int(group_id))
        .count()
    )


def _pending_identity_source(kind: str, row_id: int, source: str) -> str:
    digest = hashlib.sha256(f"{kind}:{row_id}:{source}".encode("utf-8")).hexdigest()[:16]
    return f"identity_v3:merge_pending={kind}-{int(row_id)}-{digest}"


def _vacate_group_identity_conflicts(db, rows: list[ProductGroup], target: ProductGroup, source: str) -> list[int]:
    """Canonical source target'a yazılmadan önce unique-index sahibini güvenle boşalt.

    Yalnız aynı canonical bucket içindeki kayıtlar geçici kimliğe taşınır; bucket
    dışındaki bir kayıt aynı exact identity_source'u tutuyorsa sessiz overwrite
    yerine açık hata verilir. Böylece yanlış ürünler asla merge edilmez.
    """
    row_ids = {int(row.id) for row in rows}
    owners = db.query(ProductGroup).filter(ProductGroup.identity_source == source).all()
    vacated: list[int] = []
    for owner in owners:
        if int(owner.id) == int(target.id):
            continue
        if int(owner.id) not in row_ids:
            raise RuntimeError(
                "V23.13 unsafe ProductGroup identity collision: "
                f"source={source} owner={owner.id} bucket={sorted(row_ids)}"
            )
        owner.identity_source = _pending_identity_source("group", owner.id, source)
        owner.updated_at = datetime.utcnow()
        vacated.append(int(owner.id))
    if vacated:
        db.flush()
    return vacated


def _vacate_global_identity_conflicts(db, rows: list[GlobalProduct], target: GlobalProduct, source: str) -> list[int]:
    row_ids = {int(row.id) for row in rows}
    owners = (
        db.query(GlobalProduct)
        .filter(GlobalProduct.identity_source == source, GlobalProduct.status == "ACTIVE")
        .all()
    )
    vacated: list[int] = []
    for owner in owners:
        if int(owner.id) == int(target.id):
            continue
        if int(owner.id) not in row_ids:
            raise RuntimeError(
                "V23.13 unsafe GlobalProduct identity collision: "
                f"source={source} owner={owner.id} bucket={sorted(row_ids)}"
            )
        owner.identity_source = _pending_identity_source("global", owner.id, source)
        owner.updated_at = datetime.utcnow()
        vacated.append(int(owner.id))
    if vacated:
        db.flush()
    return vacated


def converge_product_groups(db) -> dict[str, Any]:
    groups = db.query(ProductGroup).all()
    buckets: dict[str, list[ProductGroup]] = {}
    for group in groups:
        source = canonical_phone_identity_source(
            group.identity_source,
            category=group.category,
        )
        if source:
            buckets.setdefault(source, []).append(group)

    merged_groups = 0
    updated_groups = 0
    details: list[dict[str, Any]] = []

    for source, rows in buckets.items():
        canonical_key = _key(source)
        # En çok offer taşıyan grup, eşitlikte en eski ID winner.
        rows.sort(key=lambda g: (-_group_offer_count(db, g.id), int(g.id)))
        target = rows[0]

        # Canonical key başka duplicate üzerinde ise önce geçici anahtara taşı.
        key_owner = (
            db.query(ProductGroup)
            .filter(ProductGroup.group_key == canonical_key)
            .first()
        )
        if key_owner is not None and key_owner.id != target.id and key_owner in rows:
            key_owner.group_key = f"merged-pending:{key_owner.id}:{canonical_key}"[:255]
            db.flush()

        vacated_identity_owner_ids = _vacate_group_identity_conflicts(
            db, rows, target, source
        )

        if target.group_key != canonical_key or target.identity_source != source:
            target.group_key = canonical_key
            target.identity_source = source
            target.updated_at = datetime.utcnow()
            updated_groups += 1
            db.flush()

        merged_ids = []
        merged_counts: dict[str, int] = {}
        for duplicate in rows[1:]:
            if duplicate.id == target.id:
                continue
            # Unique key çakışmasını güvenli şekilde kaldır.
            duplicate.group_key = f"merged:{duplicate.id}:{duplicate.group_key}"[:255]
            db.flush()
            counts = _merge_product_groups(db, duplicate, target)
            for key, value in counts.items():
                merged_counts[key] = merged_counts.get(key, 0) + int(value)
            merged_ids.append(int(duplicate.id))
            merged_groups += 1
            db.flush()

        details.append({
            "canonical_identity_source": source,
            "canonical_group_key": canonical_key,
            "target_group_id": int(target.id),
            "merged_group_ids": merged_ids,
            "vacated_identity_owner_ids": vacated_identity_owner_ids,
            "moved": merged_counts,
        })

    return {
        "updated_group_count": updated_groups,
        "merged_group_count": merged_groups,
        "details": details,
    }


def converge_global_products(db) -> dict[str, Any]:
    products = db.query(GlobalProduct).filter(GlobalProduct.status == "ACTIVE").all()
    buckets: dict[str, list[GlobalProduct]] = {}
    for product in products:
        source = canonical_phone_identity_source(
            product.identity_source,
            category=product.category,
        )
        if source:
            buckets.setdefault(source, []).append(product)

    merged = 0
    updated = 0
    details: list[dict[str, Any]] = []

    for source, rows in buckets.items():
        canonical_key = _key(source)

        def offer_count(item: GlobalProduct) -> int:
            return (
                db.query(GlobalOffer)
                .filter(GlobalOffer.global_product_id == item.id)
                .count()
            )

        rows.sort(key=lambda item: (-offer_count(item), int(item.id)))
        target = rows[0]

        key_owner = (
            db.query(GlobalProduct)
            .filter(GlobalProduct.identity_key == canonical_key)
            .first()
        )
        if key_owner is not None and key_owner.id != target.id and key_owner in rows:
            key_owner.identity_key = f"merged-pending:{key_owner.id}:{canonical_key}"[:250]
            db.flush()

        vacated_identity_owner_ids = _vacate_global_identity_conflicts(
            db, rows, target, source
        )

        if target.identity_key != canonical_key or target.identity_source != source:
            target.identity_key = canonical_key
            target.identity_source = source
            target.updated_at = datetime.utcnow()
            updated += 1
            db.flush()

        merged_ids = []
        for duplicate in rows[1:]:
            if duplicate.id == target.id:
                continue
            duplicate.identity_key = f"merged:{duplicate.id}:{duplicate.identity_key}"[:250]
            db.flush()
            _merge_global_product_into(db, source=duplicate, target=target)
            merged_ids.append(int(duplicate.id))
            merged += 1
            db.flush()

        # Tüm raw kayıtları canonical key'e yaklaştır.
        raws = (
            db.query(RawProduct)
            .filter(RawProduct.global_product_id == target.id)
            .all()
        )
        for raw in raws:
            raw.identity_key = canonical_key
            if raw.identity_payload:
                try:
                    payload = json.loads(raw.identity_payload)
                    if isinstance(payload, dict):
                        payload["identity_key"] = canonical_key
                        payload["identity_source"] = source
                        raw.identity_payload = json.dumps(payload, ensure_ascii=False, default=str)
                except Exception:
                    pass
            raw.updated_at = datetime.utcnow()

        details.append({
            "canonical_identity_source": source,
            "canonical_identity_key": canonical_key,
            "target_global_product_id": int(target.id),
            "merged_global_product_ids": merged_ids,
            "vacated_identity_owner_ids": vacated_identity_owner_ids,
        })

    return {
        "updated_global_product_count": updated,
        "merged_global_product_count": merged,
        "details": details,
    }


def run_identity_convergence(*, db=None) -> dict[str, Any]:
    owns = db is None
    session = db or SessionLocal()
    try:
        groups = converge_product_groups(session)
        globals_ = converge_global_products(session)
        if owns:
            session.commit()
        return {
            "engine": ENGINE,
            "engine_version": VERSION,
            "success": True,
            "product_groups": groups,
            "global_products": globals_,
        }
    except Exception:
        if owns:
            session.rollback()
        raise
    finally:
        if owns:
            session.close()
