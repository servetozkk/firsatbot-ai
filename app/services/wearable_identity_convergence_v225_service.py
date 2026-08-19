from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, ProductGroup
from app.services.canonical_identity_convergence_v223_service import (
    _group_offer_count,
    _merge_product_groups,
)
from app.services.global_catalog_service import _merge_global_product_into
from app.services.product_identity_service import ProductIdentityService

ENGINE = "FIRSATAI_WEARABLE_IDENTITY_CONVERGENCE"
VERSION = "23.1.0"


def _fold(value: object) -> str:
    return ProductIdentityService.normalize_token(str(value or ""))


def _wearable_source_from_text(
    *,
    brand: str | None,
    text: str | None,
    category: str | None,
) -> str | None:
    folded = _fold(text)
    category_folded = _fold(category)
    if not (
        "akilli saat" in category_folded
        or "giyilebilir teknoloji" in category_folded
        or " watch " in f" {folded} "
    ):
        return None

    normalized_brand = _fold(brand)
    patterns = (
        (r"\bredmi\s+watch\s+(\d{1,2})(?:\s+(active|lite|pro))?\b", "redmi watch {}", "xiaomi"),
        (r"\bgalaxy\s+watch\s+(\d{1,2})(?:\s+(ultra|pro|classic|active))?\b", "galaxy watch {}", "samsung"),
        (r"\bapple\s+watch\s+series\s+(\d{1,2})(?:\s+(ultra|se))?\b", "apple watch series {}", "apple"),
    )
    for pattern, family_template, default_brand in patterns:
        match = re.search(pattern, folded, re.I)
        if match:
            parts = [
                f"brand={normalized_brand or default_brand}",
                f"family={family_template.format(match.group(1))}",
            ]
            variant = " ".join(str(match.group(2) or "").split())
            if variant:
                parts.append(f"variant={variant}")
            return "identity_v3:" + "|".join(parts)

    generic = re.search(
        r"\b(?:huawei\s+|honor\s+)?watch\s+(gt|fit)\s*(\d{1,2})(?:\s+(pro|active))?\b",
        folded,
        re.I,
    )
    if generic:
        parts = [
            f"brand={normalized_brand or 'huawei'}",
            f"family=watch {generic.group(1)} {generic.group(2)}",
        ]
        if generic.group(3):
            parts.append(f"variant={generic.group(3)}")
        return "identity_v3:" + "|".join(parts)

    return None


def _key(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]


def _source_parts(source: str | None) -> dict[str, str]:
    value = str(source or "").strip()
    if not value.startswith("identity_v3:"):
        return {}
    result: dict[str, str] = {}
    for chunk in value.split(":", 1)[1].split("|"):
        if "=" not in chunk:
            continue
        key, raw = chunk.split("=", 1)
        if key.strip() and raw.strip():
            result[key.strip()] = raw.strip()
    return result


def _strongest_wearable_source(
    *,
    brand: str | None,
    texts: tuple[str | None, ...],
    category: str | None,
) -> str | None:
    """V23.1: Ayrı alanlardan çıkarılan en güçlü wearable kimliği seçilir."""
    candidates: list[tuple[int, int, str]] = []
    for index, text in enumerate(texts):
        source = _wearable_source_from_text(
            brand=brand,
            text=text,
            category=category,
        )
        if not source:
            continue
        parts = _source_parts(source)
        variant = str(parts.get("variant") or "").strip()
        family = str(parts.get("family") or "").strip()
        if not family:
            continue
        strength = 200 if variant else 100
        strength += index
        candidates.append((strength, index, source))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return candidates[0][2]


def _canonical_group_source(group: ProductGroup) -> str | None:
    return _strongest_wearable_source(
        brand=group.brand,
        texts=(
            str(group.identity_source or ""),
            str(group.model or ""),
            str(group.canonical_name or ""),
        ),
        category=group.category,
    )


def _canonical_global_source(product: GlobalProduct) -> str | None:
    return _strongest_wearable_source(
        brand=product.normalized_brand,
        texts=(
            str(product.identity_source or ""),
            str(product.family or ""),
            str(product.model or ""),
            str(product.canonical_name or ""),
        ),
        category=product.category,
    )


def converge_wearable_groups(db) -> dict[str, Any]:
    buckets: dict[str, list[ProductGroup]] = {}
    for group in db.query(ProductGroup).all():
        source = _canonical_group_source(group)
        if source:
            buckets.setdefault(source, []).append(group)

    merged = 0
    updated = 0
    details = []

    for source, rows in buckets.items():
        canonical_key = _key(source)
        canonical_rows = [
            row for row in rows
            if str(row.group_key or "") == canonical_key
            and str(row.identity_source or "").strip() == source
        ]
        if canonical_rows:
            target = min(canonical_rows, key=lambda row: int(row.id))
        else:
            exact_source_rows = [row for row in rows if str(row.identity_source or "").strip() == source]
            target = min(exact_source_rows or rows, key=lambda row: int(row.id))
        rows = [target] + [row for row in rows if row.id != target.id]

        key_owner = db.query(ProductGroup).filter(ProductGroup.group_key == canonical_key).first()
        if key_owner is not None and key_owner.id != target.id and key_owner in rows:
            key_owner.group_key = f"merged-pending:{key_owner.id}:{canonical_key}"[:255]
            db.flush()

        if target.group_key != canonical_key or target.identity_source != source:
            target.group_key = canonical_key
            target.identity_source = source
            # Model alanını canonical family+variant seviyesinde sadeleştir.
            bits = [chunk.split("=", 1)[1] for chunk in source.split("|") if chunk.startswith(("family=", "variant="))]
            if bits:
                target.model = " ".join(bits)
            target.updated_at = datetime.utcnow()
            updated += 1
            db.flush()

        merged_ids = []
        for duplicate in rows[1:]:
            if duplicate.id == target.id:
                continue
            duplicate.group_key = f"merged:{duplicate.id}:{duplicate.group_key}"[:255]
            db.flush()
            _merge_product_groups(db, duplicate, target)
            db.flush()
            merged_ids.append(int(duplicate.id))
            merged += 1

        details.append({
            "canonical_identity_source": source,
            "target_group_id": int(target.id),
            "merged_group_ids": merged_ids,
        })

    return {"updated_group_count": updated, "merged_group_count": merged, "details": details}


def converge_wearable_globals(db) -> dict[str, Any]:
    buckets: dict[str, list[GlobalProduct]] = {}
    for product in db.query(GlobalProduct).filter(GlobalProduct.status == "ACTIVE").all():
        source = _canonical_global_source(product)
        if source:
            buckets.setdefault(source, []).append(product)

    merged = 0
    updated = 0
    details = []

    for source, rows in buckets.items():
        canonical_key = _key(source)

        canonical_rows = [
            row for row in rows
            if str(row.identity_key or "") == canonical_key
            and str(row.identity_source or "").strip() == source
        ]
        if canonical_rows:
            target = min(canonical_rows, key=lambda row: int(row.id))
        else:
            exact_source_rows = [row for row in rows if str(row.identity_source or "").strip() == source]
            target = min(exact_source_rows or rows, key=lambda row: int(row.id))
        rows = [target] + [row for row in rows if row.id != target.id]

        owner = db.query(GlobalProduct).filter(GlobalProduct.identity_key == canonical_key).first()
        if owner is not None and owner.id != target.id and owner in rows:
            owner.identity_key = f"merged-pending:{owner.id}:{canonical_key}"[:250]
            db.flush()

        if target.identity_key != canonical_key or target.identity_source != source:
            target.identity_key = canonical_key
            target.identity_source = source
            source_parts = {}
            for chunk in source.split(":", 1)[-1].split("|"):
                if "=" in chunk:
                    k, v = chunk.split("=", 1)
                    source_parts[k] = v
            target.normalized_brand = source_parts.get("brand") or target.normalized_brand
            target.family = source_parts.get("family") or target.family
            target.variant = source_parts.get("variant") or None
            target.model = " ".join(
                x for x in (target.family, target.variant) if x
            )
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
            db.flush()
            merged_ids.append(int(duplicate.id))
            merged += 1

        details.append({
            "canonical_identity_source": source,
            "target_global_product_id": int(target.id),
            "merged_global_product_ids": merged_ids,
        })

    return {"updated_global_product_count": updated, "merged_global_product_count": merged, "details": details}


def run_wearable_convergence(*, db=None) -> dict[str, Any]:
    owns = db is None
    session = db or SessionLocal()
    try:
        groups = converge_wearable_groups(session)
        globals_ = converge_wearable_globals(session)
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
