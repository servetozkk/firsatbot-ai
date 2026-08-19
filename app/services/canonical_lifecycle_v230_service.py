from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.database.database import SessionLocal, engine
from app.database.models import GlobalProduct, ProductGroup

ENGINE = "FIRSATAI_CANONICAL_LIFECYCLE_SINGLE_SOURCE"
VERSION = "23.1.0"


def canonical_key(identity_source: str) -> str:
    return hashlib.sha256(str(identity_source or "").encode("utf-8")).hexdigest()[:32]


def normalize_identity_source(value: object) -> str:
    return str(value or "").strip()


def _identity_v3_parts(source: str | None) -> dict[str, str]:
    value = normalize_identity_source(source)
    if not value.startswith("identity_v3:"):
        return {}
    result: dict[str, str] = {}
    for chunk in value.split(":", 1)[1].split("|"):
        if "=" not in chunk:
            continue
        key, raw = chunk.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if key and raw:
            result[key] = raw
    return result


def _wearable_family_needs_variant(parts: dict[str, str]) -> bool:
    family = str(parts.get("family") or "").casefold().strip()
    return bool(
        re.match(r"^(?:redmi watch|galaxy watch|apple watch series)\s+\d+", family)
    )


def _explicit_variant_from_text(value: object) -> str | None:
    folded = str(value or "").casefold()
    match = re.search(
        r"\b(?:redmi\s+watch|galaxy\s+watch|apple\s+watch\s+series)\s+\d{1,2}\s+(active|lite|pro|ultra|classic)\b",
        folded,
        flags=re.IGNORECASE,
    )
    return str(match.group(1)).casefold() if match else None


def _promotable_wearable_source(
    *,
    requested_source: str,
    existing_source: str,
    evidence_texts: tuple[object, ...],
) -> bool:
    requested = _identity_v3_parts(requested_source)
    existing = _identity_v3_parts(existing_source)
    if not requested or not existing:
        return False

    requested_variant = str(requested.get("variant") or "").casefold().strip()
    if not requested_variant or existing.get("variant"):
        return False

    if str(requested.get("brand") or "") != str(existing.get("brand") or ""):
        return False
    if str(requested.get("family") or "") != str(existing.get("family") or ""):
        return False

    evidence_variants = {
        variant
        for variant in (
            _explicit_variant_from_text(text)
            for text in evidence_texts
        )
        if variant
    }
    return evidence_variants == {requested_variant}


def _wearable_base_source(source: str) -> str | None:
    parts = _identity_v3_parts(source)
    if not parts or not _wearable_family_needs_variant(parts):
        return None
    if not parts.get("variant"):
        return source

    ordered = []
    for key in ("brand", "family"):
        value = parts.get(key)
        if value:
            ordered.append(f"{key}={value}")
    return "identity_v3:" + "|".join(ordered) if ordered else None


def resolve_product_group(db, identity_source: str, group_key: str | None = None) -> ProductGroup | None:
    source = normalize_identity_source(identity_source)
    if not source:
        return None
    expected_key = group_key or canonical_key(source)

    # identity_source fiziksel ürün kimliğinin asıl sözleşmesidir.
    row = (
        db.query(ProductGroup)
        .filter(ProductGroup.identity_source == source)
        .order_by(ProductGroup.id.asc())
        .first()
    )
    if row is not None:
        if row.group_key != expected_key:
            row.group_key = expected_key
            row.updated_at = datetime.utcnow()
            db.flush()
        return row

    # V23.1: Eski wearable base identity metadata içinde aynı explicit
    # varyantı taşıyorsa yeni kayıt açmadan yerinde promote edilir.
    base_source = _wearable_base_source(source)
    if base_source and base_source != source:
        base_rows = (
            db.query(ProductGroup)
            .filter(ProductGroup.identity_source == base_source)
            .order_by(ProductGroup.id.asc())
            .all()
        )
        promotable = [
            candidate
            for candidate in base_rows
            if _promotable_wearable_source(
                requested_source=source,
                existing_source=base_source,
                evidence_texts=(candidate.model, candidate.canonical_name),
            )
        ]
        if len(promotable) == 1:
            row = promotable[0]
            row.identity_source = source
            row.group_key = expected_key
            row.updated_at = datetime.utcnow()
            db.flush()
            print(
                "V23.1 wearable ProductGroup identity promote:",
                f"group={row.id}",
                base_source,
                "->",
                source,
            )
            return row

    # Eski kayıtta source boş ancak key doğruysa kaydı sahiplen.
    row = (
        db.query(ProductGroup)
        .filter(ProductGroup.group_key == expected_key)
        .order_by(ProductGroup.id.asc())
        .first()
    )
    if row is not None:
        existing_source = normalize_identity_source(row.identity_source)
        if existing_source and existing_source != source:
            raise ValueError(
                "Canonical ProductGroup key başka identity_source tarafından kullanılıyor."
            )
        row.identity_source = source
        row.updated_at = datetime.utcnow()
        db.flush()
        return row
    return None


def resolve_global_product(db, identity_source: str, identity_key: str | None = None) -> GlobalProduct | None:
    source = normalize_identity_source(identity_source)
    if not source:
        return None
    expected_key = identity_key or canonical_key(source)

    row = (
        db.query(GlobalProduct)
        .filter(
            GlobalProduct.identity_source == source,
            GlobalProduct.status == "ACTIVE",
        )
        .order_by(GlobalProduct.id.asc())
        .first()
    )
    if row is not None:
        if row.identity_key != expected_key:
            row.identity_key = expected_key
            row.updated_at = datetime.utcnow()
            db.flush()
        return row

    # V23.1: ProductGroup ile aynı wearable contract promotion GlobalProduct
    # tarafında da uygulanır; yalnız metadata tek ve açık varyant kanıtı verirse.
    base_source = _wearable_base_source(source)
    if base_source and base_source != source:
        base_rows = (
            db.query(GlobalProduct)
            .filter(
                GlobalProduct.identity_source == base_source,
                GlobalProduct.status == "ACTIVE",
            )
            .order_by(GlobalProduct.id.asc())
            .all()
        )
        promotable = [
            candidate
            for candidate in base_rows
            if _promotable_wearable_source(
                requested_source=source,
                existing_source=base_source,
                evidence_texts=(
                    candidate.variant,
                    candidate.model,
                    candidate.canonical_name,
                ),
            )
        ]
        if len(promotable) == 1:
            row = promotable[0]
            row.identity_source = source
            row.identity_key = expected_key
            requested_parts = _identity_v3_parts(source)
            row.variant = requested_parts.get("variant") or row.variant
            row.updated_at = datetime.utcnow()
            db.flush()
            print(
                "V23.1 wearable GlobalProduct identity promote:",
                f"global={row.id}",
                base_source,
                "->",
                source,
            )
            return row

    row = (
        db.query(GlobalProduct)
        .filter(
            GlobalProduct.identity_key == expected_key,
            GlobalProduct.status == "ACTIVE",
        )
        .order_by(GlobalProduct.id.asc())
        .first()
    )
    if row is not None:
        existing_source = normalize_identity_source(row.identity_source)
        if existing_source and existing_source != source:
            raise ValueError(
                "Canonical GlobalProduct key başka identity_source tarafından kullanılıyor."
            )
        row.identity_source = source
        row.updated_at = datetime.utcnow()
        db.flush()
        return row
    return None


def install_database_guards() -> dict[str, Any]:
    # Lazy import circular dependency'yi engeller: alias service GlobalCatalog kullanır.
    from app.services.canonical_alias_reliability_v227_service import audit_all_aliases

    # Önce geçmiş duplicate kayıtları tekilleştir. Sonra DB-level guard kur.
    alias_result = audit_all_aliases()
    statements = (
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_v230_product_groups_identity_source
        ON product_groups(identity_source)
        WHERE identity_source IS NOT NULL AND trim(identity_source) <> ''
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_v230_global_products_active_identity_source
        ON global_products(identity_source)
        WHERE identity_source IS NOT NULL AND trim(identity_source) <> '' AND status = 'ACTIVE'
        """,
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    return {
        "engine": ENGINE,
        "engine_version": VERSION,
        "success": True,
        "database_guards": [
            "ux_v230_product_groups_identity_source",
            "ux_v230_global_products_active_identity_source",
        ],
        "alias_audit": alias_result,
    }


def lifecycle_status(identity_source: str | None = None) -> dict[str, Any]:
    db = SessionLocal()
    try:
        source_filter = normalize_identity_source(identity_source)
        group_query = db.query(ProductGroup)
        global_query = db.query(GlobalProduct).filter(GlobalProduct.status == "ACTIVE")
        if source_filter:
            group_query = group_query.filter(ProductGroup.identity_source == source_filter)
            global_query = global_query.filter(GlobalProduct.identity_source == source_filter)

        groups = group_query.order_by(ProductGroup.id.asc()).all()
        globals_ = global_query.order_by(GlobalProduct.id.asc()).all()

        group_map: dict[str, list[int]] = {}
        global_map: dict[str, list[int]] = {}
        for row in groups:
            source = normalize_identity_source(row.identity_source)
            if source:
                group_map.setdefault(source, []).append(int(row.id))
        for row in globals_:
            source = normalize_identity_source(row.identity_source)
            if source:
                global_map.setdefault(source, []).append(int(row.id))

        duplicates_groups = {k: v for k, v in group_map.items() if len(v) > 1}
        duplicates_globals = {k: v for k, v in global_map.items() if len(v) > 1}

        mappings = []
        all_sources = sorted(set(group_map) | set(global_map))
        for source in all_sources:
            mappings.append({
                "identity_source": source,
                "canonical_key": canonical_key(source),
                "product_group_ids": group_map.get(source, []),
                "global_product_ids": global_map.get(source, []),
                "product_group_id": (group_map.get(source) or [None])[0],
                "global_product_id": (global_map.get(source) or [None])[0],
            })

        contract_violations = []
        for source in all_sources:
            parts = _identity_v3_parts(source)
            if not parts or not _wearable_family_needs_variant(parts):
                continue
            if parts.get("variant"):
                continue

            group_ids = group_map.get(source, [])
            global_ids = global_map.get(source, [])
            evidence_variants = set()

            for group_id in group_ids:
                row = db.get(ProductGroup, group_id)
                if row is not None:
                    for value in (row.model, row.canonical_name):
                        variant = _explicit_variant_from_text(value)
                        if variant:
                            evidence_variants.add(variant)

            for global_id in global_ids:
                row = db.get(GlobalProduct, global_id)
                if row is not None:
                    for value in (row.variant, row.model, row.canonical_name):
                        variant = _explicit_variant_from_text(value)
                        if variant:
                            evidence_variants.add(variant)

            if evidence_variants:
                contract_violations.append({
                    "identity_source": source,
                    "product_group_ids": group_ids,
                    "global_product_ids": global_ids,
                    "explicit_variant_evidence": sorted(evidence_variants),
                    "reason": "WEARABLE_VARIANT_DROPPED",
                })

        return {
            "engine": ENGINE,
            "engine_version": VERSION,
            "identity_source_filter": source_filter or None,
            "mapping_count": len(mappings),
            "duplicate_product_group_identity_count": len(duplicates_groups),
            "duplicate_global_product_identity_count": len(duplicates_globals),
            "duplicate_product_groups": duplicates_groups,
            "duplicate_global_products": duplicates_globals,
            "identity_contract_violation_count": len(contract_violations),
            "identity_contract_violations": contract_violations,
            "single_source_of_truth": (
                not duplicates_groups
                and not duplicates_globals
                and not contract_violations
            ),
            "mappings": mappings,
        }
    finally:
        db.close()
