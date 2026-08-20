from __future__ import annotations

from app.services.production_integrity_guard_v236363_service import (
    ProductionIntegrityGuardV236363,
)

import json
from datetime import datetime

from app.database.database import SessionLocal
from app.database.models import GlobalProduct, ProductGroup, RawProduct
from app.models.product import Product
from app.services.canonical_lifecycle_v230_service import canonical_key
from app.services.product_identity_service import ProductIdentityService

_COMPATIBILITY_BRANDS = {"apple", "samsung", "xiaomi"}


def _norm(value):
    return ProductIdentityService.normalize_token(value)


def _specs(value):
    if not value:
        return None
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def _product_from_raw(raw: RawProduct) -> Product:
    return Product(
        name=raw.title_raw or "",
        price=float(raw.price_raw or 0),
        old_price=raw.old_price_raw,
        rating=None,
        review_count=None,
        seller=raw.seller_raw or "",
        url=raw.source_url or "",
        image=raw.image_raw,
        brand=raw.brand_raw,
        model=raw.model_raw,
        category=raw.category_raw,
        description=raw.description_raw,
        specifications=_specs(raw.specifications_raw),
        stock_status=raw.stock_raw,
        source_site=raw.store_code,
        product_code=raw.store_product_id,
    )


def run_accessory_identity_convergence_v236342() -> dict:
    """Repair only proven compatibility-brand contamination, fail closed.

    A GlobalProduct is eligible only when every MATCHED raw row linked to it is
    an accessory, all rows produce exactly the same corrected identity key,
    the current canonical brand is one of the known compatibility targets, and
    the corrected identity/key is unused by another active GlobalProduct or
    ProductGroup. No offer/variant/price rows are rewritten.
    """
    db = SessionLocal()
    checked = repaired = unsafe = raw_relinked = group_repaired = 0
    affected: set[int] = set()
    try:
        products = (
            db.query(GlobalProduct)
            .filter(
                GlobalProduct.status == "ACTIVE",
                GlobalProduct.normalized_brand.in_(_COMPATIBILITY_BRANDS),
            )
            .all()
        )
        for gp in products:
            raws = (
                db.query(RawProduct)
                .filter(
                    RawProduct.global_product_id == gp.id,
                    RawProduct.reconciliation_status == "MATCHED",
                )
                .all()
            )
            if not raws:
                continue

            explained = []
            eligible = True
            for raw in raws:
                product = _product_from_raw(raw)
                if not ProductIdentityService._is_accessory_identity(product):
                    eligible = False
                    break
                info = ProductIdentityService.explain(product)
                explained.append((raw, info))
            if not eligible or not explained:
                continue

            checked += 1
            keys = {str(info.get("identity_key") or "") for _, info in explained}
            sources = {str(info.get("identity_source") or "") for _, info in explained}
            brands = {_norm(info.get("normalized_brand")) for _, info in explained}
            families = {_norm(info.get("family")) for _, info in explained}
            reasons = []
            if len(keys) != 1 or "" in keys:
                reasons.append("RAW_IDENTITY_KEY_DISAGREEMENT")
            if len(sources) != 1 or "" in sources:
                reasons.append("RAW_IDENTITY_SOURCE_DISAGREEMENT")
            if len(brands) != 1 or "" in brands:
                reasons.append("RAW_BRAND_DISAGREEMENT")
            corrected_brand = next(iter(brands), "")
            if corrected_brand == _norm(gp.normalized_brand):
                continue
            if corrected_brand in _COMPATIBILITY_BRANDS:
                reasons.append("NO_NON_COMPATIBILITY_BRAND_EVIDENCE")
            if len(families) != 1 or _norm(gp.family) not in families:
                reasons.append("FAMILY_CONFLICT")

            info = explained[0][1]
            new_key = str(info.get("identity_key") or "")
            new_source = str(info.get("identity_source") or "")
            collision_gp = (
                db.query(GlobalProduct)
                .filter(
                    GlobalProduct.id != gp.id,
                    GlobalProduct.status == "ACTIVE",
                    (GlobalProduct.identity_key == new_key) |
                    (GlobalProduct.identity_source == new_source),
                )
                .first()
            )
            if collision_gp is not None:
                reasons.append("GLOBAL_PRODUCT_COLLISION")

            old_source = str(gp.identity_source or "")
            groups = (
                db.query(ProductGroup)
                .filter(ProductGroup.identity_source == old_source)
                .all()
                if old_source else []
            )
            for group in groups:
                if _norm(group.brand) not in {"", corrected_brand}:
                    reasons.append("PRODUCT_GROUP_BRAND_CONFLICT")
                if _norm(group.model) and _norm(group.model) != _norm(gp.family):
                    reasons.append("PRODUCT_GROUP_MODEL_CONFLICT")
            new_group_key = canonical_key(new_source)
            group_collision = (
                db.query(ProductGroup)
                .filter(
                    ProductGroup.group_key == new_group_key,
                    ~ProductGroup.id.in_([g.id for g in groups] or [-1]),
                )
                .first()
            )
            if group_collision is not None:
                reasons.append("PRODUCT_GROUP_COLLISION")

            if reasons:
                unsafe += 1
                continue

            now = datetime.utcnow()
            gp.identity_key = new_key
            gp.identity_source = new_source
            gp.normalized_brand = str(info.get("normalized_brand") or "") or None
            gp.family = str(info.get("family") or "") or gp.family
            gp.model = str(info.get("normalized_model") or "") or gp.model
            gp.variant = str(info.get("variant") or "") or None
            # Accessory capabilities must not inherit target-device attributes.
            gp.ram_gb = None
            gp.storage_gb = None
            gp.screen_inch = None
            gp.updated_at = now

            for raw, raw_info in explained:
                raw.identity_key = str(raw_info.get("identity_key") or "") or raw.identity_key
                raw.identity_payload = json.dumps(raw_info, ensure_ascii=False)
                raw.updated_at = now
                raw_relinked += 1

            for group in groups:
                group.identity_source = new_source
                group.group_key = new_group_key
                group.brand = corrected_brand
                group.updated_at = now
                group_repaired += 1

            repaired += 1
            affected.add(int(gp.id))

        ProductionIntegrityGuardV236363.assert_clean(
            db,
            context="v236366_accessory_identity_convergence",
        )
        db.commit()
        return {
            "runtime_version": "23.63.42",
            "checked_candidate_count": checked,
            "repaired_global_product_count": repaired,
            "repaired_raw_product_count": raw_relinked,
            "repaired_product_group_count": group_repaired,
            "unsafe_count": unsafe,
            "affected_global_product_count": len(affected),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
