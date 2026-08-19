from __future__ import annotations

import hashlib
import json
from datetime import datetime
from contextlib import contextmanager
import threading
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.exc import IntegrityError

from app.database.models import (
    GlobalOffer,
    GlobalOfferPriceHistory,
    GlobalPriceAlert,
    GlobalProduct,
    GlobalProductVariant,
    RawProduct,
)
from app.services.product_identity_service import ProductIdentityService
from app.services.canonical_lifecycle_v230_service import resolve_global_product


def _clean(value: Any) -> str | None:
    text = " ".join(str(value or "").split()).strip()
    return text or None


def _safe_model_code(value: Any) -> str | None:
    """Keep real SKU/ASIN codes, reject specification-derived pseudo codes."""
    cleaned = _clean(value)
    if cleaned and ProductIdentityService._is_pseudo_model_code(cleaned):
        return None
    return cleaned


def _store_code(product: Any) -> str:
    source = _clean(getattr(product, "source_site", None)) or ""
    host = (urlsplit(str(getattr(product, "url", "") or "")).hostname or "").casefold()
    host = host.removeprefix("www.")

    aliases = {
        "trendyol.com": "trendyol",
        "hepsiburada.com": "hepsiburada",
        "amazon.com.tr": "amazon",
        "n11.com": "n11",
        "pazarama.com": "pazarama",
        "teknosa.com": "teknosa",
        "mediamarkt.com.tr": "mediamarkt",
        "vatanbilgisayar.com": "vatan",
        "idefix.com": "idefix",
        "pttavm.com": "pttavm",
        "beymen.com": "beymen",
    }
    for domain, code in aliases.items():
        if host == domain or host.endswith("." + domain):
            return code

    normalized = source.casefold().replace(" ", "")
    for code in aliases.values():
        if code in normalized:
            return code
    return normalized or "unknown"


def _json(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _raw_fingerprint(product: Any, store_code: str) -> str:
    value = "|".join(
        [
            store_code,
            str(getattr(product, "product_code", "") or ""),
            str(getattr(product, "url", "") or ""),
        ]
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _variant_key(identity: dict[str, Any]) -> str:
    parts = [
        f"color={identity.get('color')}" if identity.get("color") else "",
        f"network={identity.get('network')}" if identity.get("network") else "",
        f"model_code={_safe_model_code(identity.get('model_code'))}" if _safe_model_code(identity.get("model_code")) else "",
    ]
    value = "|".join(part for part in parts if part)
    return value or "default"


def _display_name(product: Any, identity: dict[str, Any]) -> str:
    name = _clean(getattr(product, "name", None))
    if name:
        return name

    parts = [
        identity.get("normalized_brand"),
        identity.get("family"),
        identity.get("variant"),
    ]
    return " ".join(str(part) for part in parts if part).strip() or "Bilinmeyen Ürün"




_preferred_catalog_target = threading.local()


def get_preferred_global_product_id() -> int | None:
    value = getattr(_preferred_catalog_target, "global_product_id", None)
    return int(value) if value is not None else None


@contextmanager
def preferred_global_product(global_product_id: int | None):
    previous = getattr(_preferred_catalog_target, "global_product_id", None)
    _preferred_catalog_target.global_product_id = (
        int(global_product_id) if global_product_id is not None else None
    )
    try:
        yield
    finally:
        _preferred_catalog_target.global_product_id = previous


def _merged_identity_key(product_id: int, old_key: str | None) -> str:
    base = str(old_key or "merged").strip() or "merged"
    return f"merged:{int(product_id)}:{base}"[:250]


def _merge_global_product_into(
    db,
    *,
    source: GlobalProduct,
    target: GlobalProduct,
) -> None:
    if int(source.id) == int(target.id):
        return

    source_raws = (
        db.query(RawProduct)
        .filter(RawProduct.global_product_id == source.id)
        .all()
    )
    for raw in source_raws:
        raw.global_product_id = target.id
        raw.global_variant_id = None
        raw.updated_at = datetime.utcnow()

    source_offers = (
        db.query(GlobalOffer)
        .filter(GlobalOffer.global_product_id == source.id)
        .all()
    )
    for offer in source_offers:
        offer.global_product_id = target.id
        offer.global_variant_id = None
        offer.updated_at = datetime.utcnow()

    source_variant_ids = [
        row.id
        for row in (
            db.query(GlobalProductVariant)
            .filter(GlobalProductVariant.global_product_id == source.id)
            .all()
        )
    ]

    (
        db.query(GlobalOfferPriceHistory)
        .filter(GlobalOfferPriceHistory.global_product_id == source.id)
        .update(
            {GlobalOfferPriceHistory.global_product_id: target.id},
            synchronize_session=False,
        )
    )
    (
        db.query(GlobalPriceAlert)
        .filter(GlobalPriceAlert.global_product_id == source.id)
        .update(
            {GlobalPriceAlert.global_product_id: target.id},
            synchronize_session=False,
        )
    )

    source.identity_key = _merged_identity_key(source.id, source.identity_key)
    source.status = "MERGED"
    source.raw_product_count = 0
    source.active_offer_count = 0
    source.updated_at = datetime.utcnow()
    db.flush()


def sync_raw_and_global_catalog(
    *,
    db,
    product: Any,
    legacy_product_id: int | None,
    identity_info: dict[str, Any] | None = None,
) -> tuple[RawProduct, GlobalProduct, GlobalProductVariant]:
    """
    Scraper ürününü önce ham havuza, ardından global kataloğa bağlar.

    Bu fonksiyon mevcut products/product_groups/product_offers akışını bozmaz.
    Yeni katalog çekirdeği paralel olarak doldurulur.
    """
    identity = identity_info or ProductIdentityService.explain(product)
    identity_key = str(identity.get("identity_key") or "").strip()
    if not identity_key:
        raise ValueError("Global katalog için ürün kimliği üretilemedi.")

    now = datetime.utcnow()
    store_code = _store_code(product)
    fingerprint = _raw_fingerprint(product, store_code)

    raw = (
        db.query(RawProduct)
        .filter(RawProduct.fingerprint == fingerprint)
        .first()
    )
    if raw is None:
        raw = RawProduct(
            fingerprint=fingerprint,
            store_code=store_code,
            store_product_id=_clean(getattr(product, "product_code", None)),
            source_url=str(getattr(product, "url", "") or ""),
            title_raw=_clean(getattr(product, "name", None)) or "Bilinmeyen Ürün",
            brand_raw=_clean(getattr(product, "brand", None)),
            model_raw=_clean(getattr(product, "model", None)),
            seller_raw=_clean(getattr(product, "seller", None)),
            price_raw=float(getattr(product, "price", 0) or 0),
            old_price_raw=(
                float(getattr(product, "old_price"))
                if getattr(product, "old_price", None) is not None
                else None
            ),
            stock_raw=_clean(getattr(product, "stock_status", None)),
            image_raw=_clean(getattr(product, "image", None)),
            gallery_raw=_json(getattr(product, "image_gallery", None)),
            specifications_raw=_json(getattr(product, "specifications", None)),
            description_raw=_clean(getattr(product, "description", None)),
            category_raw=_clean(getattr(product, "category", None)),
            legacy_product_id=legacy_product_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(raw)
        db.flush()
    else:
        raw.title_raw = _clean(getattr(product, "name", None)) or raw.title_raw
        raw.brand_raw = _clean(getattr(product, "brand", None)) or raw.brand_raw
        raw.model_raw = _clean(getattr(product, "model", None)) or raw.model_raw
        raw.seller_raw = _clean(getattr(product, "seller", None)) or raw.seller_raw
        raw.price_raw = float(getattr(product, "price", 0) or raw.price_raw or 0)
        raw.old_price_raw = (
            float(getattr(product, "old_price"))
            if getattr(product, "old_price", None) is not None
            else raw.old_price_raw
        )
        raw.stock_raw = _clean(getattr(product, "stock_status", None)) or raw.stock_raw
        raw.image_raw = _clean(getattr(product, "image", None)) or raw.image_raw
        raw.gallery_raw = _json(getattr(product, "image_gallery", None)) or raw.gallery_raw
        raw.specifications_raw = _json(getattr(product, "specifications", None)) or raw.specifications_raw
        raw.description_raw = _clean(getattr(product, "description", None)) or raw.description_raw
        raw.category_raw = _clean(getattr(product, "category", None)) or raw.category_raw
        raw.legacy_product_id = legacy_product_id or raw.legacy_product_id
        raw.last_seen_at = now
        raw.updated_at = now

    preferred_id = get_preferred_global_product_id()
    preferred_product = (
        db.get(GlobalProduct, preferred_id)
        if preferred_id is not None
        else None
    )
    identity_source = _clean(identity.get("identity_source"))
    # V23.0 SINGLE SOURCE OF TRUTH: GlobalProduct ve ProductGroup aynı
    # canonical resolver sözleşmesini kullanır.
    identity_owner = resolve_global_product(
        db,
        identity_source=identity_source or "",
        identity_key=identity_key,
    )
    if identity_owner is not None:
        print(
            "V23.0 canonical resolver GlobalProduct yeniden kullanıldı:",
            f"global={identity_owner.id}",
            identity_source,
        )

    if preferred_id is not None and preferred_product is None:
        raise ValueError(
            f"Tercih edilen global ürün bulunamadı: {preferred_id}"
        )

    if preferred_product is not None:
        if identity_owner is not None and identity_owner.id != preferred_product.id:
            _merge_global_product_into(
                db,
                source=identity_owner,
                target=preferred_product,
            )

        global_product = preferred_product
        global_product.identity_key = identity_key
        global_product.identity_source = _clean(identity.get("identity_source"))
        global_product.normalized_brand = _clean(identity.get("normalized_brand"))
        global_product.family = _clean(identity.get("family"))
        global_product.model = _clean(identity.get("normalized_model"))
        global_product.variant = _clean(identity.get("variant"))
        global_product.ram_gb = identity.get("ram_gb")
        global_product.storage_gb = identity.get("storage_gb")
        global_product.screen_inch = identity.get("screen_inch")
        global_product.model_code = _safe_model_code(identity.get("model_code"))
        global_product.status = "ACTIVE"
        global_product.updated_at = now
    else:
        global_product = identity_owner

    if global_product is None:
        candidate_global = GlobalProduct(
            identity_key=identity_key,
            identity_source=_clean(identity.get("identity_source")),
            canonical_name=_display_name(product, identity),
            normalized_brand=_clean(identity.get("normalized_brand")),
            family=_clean(identity.get("family")),
            model=_clean(identity.get("normalized_model")),
            variant=_clean(identity.get("variant")),
            ram_gb=identity.get("ram_gb"),
            storage_gb=identity.get("storage_gb"),
            screen_inch=identity.get("screen_inch"),
            model_code=_safe_model_code(identity.get("model_code")),
            category=_clean(getattr(product, "category", None)),
            primary_image=_clean(getattr(product, "image", None)),
            raw_product_count=0,
            active_offer_count=0,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        try:
            with db.begin_nested():
                db.add(candidate_global)
                db.flush()
            global_product = candidate_global
            print(
                "V23.0 canonical resolver GlobalProduct ilk kez oluşturuldu:",
                f"global={global_product.id}",
                identity_source,
            )
        except IntegrityError:
            # DB unique guard yarışta ikinci create'i engellediyse mevcut kaydı al.
            global_product = resolve_global_product(
                db,
                identity_source=identity_source or "",
                identity_key=identity_key,
            )
            if global_product is None:
                raise
            print(
                "V23.0 DB guard GlobalProduct yeniden kullanıldı:",
                f"global={global_product.id}",
                identity_source,
            )
    else:
        if not global_product.primary_image and getattr(product, "image", None):
            global_product.primary_image = str(product.image)
        if not global_product.category and getattr(product, "category", None):
            global_product.category = str(product.category)
        global_product.updated_at = now

    variant_key = _variant_key(identity)
    variant = (
        db.query(GlobalProductVariant)
        .filter(
            GlobalProductVariant.global_product_id == global_product.id,
            GlobalProductVariant.variant_key == variant_key,
        )
        .first()
    )
    if variant is None:
        variant = GlobalProductVariant(
            global_product_id=global_product.id,
            variant_key=variant_key,
            color=_clean(identity.get("color")),
            network=_clean(identity.get("network")),
            model_code=_safe_model_code(identity.get("model_code")),
            primary_image=_clean(getattr(product, "image", None)),
            created_at=now,
            updated_at=now,
        )
        db.add(variant)
        db.flush()
    else:
        if not variant.primary_image and getattr(product, "image", None):
            variant.primary_image = str(product.image)
        variant.updated_at = now

    raw.global_product_id = global_product.id
    raw.global_variant_id = variant.id

    # V23.63.41: variant binding is raw-product scoped. Never overwrite every
    # offer/alert/history of the GlobalProduct with the currently reconciled
    # raw product's variant; that caused cross-offer referential drift.
    linked_offers = (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.global_product_id == global_product.id,
            GlobalOffer.raw_product_id == raw.id,
        )
        .all()
    )
    for linked_offer in linked_offers:
        linked_offer.global_variant_id = variant.id
        linked_histories = (
            db.query(GlobalOfferPriceHistory)
            .filter(GlobalOfferPriceHistory.global_offer_id == linked_offer.id)
            .all()
        )
        for history in linked_histories:
            history.global_variant_id = variant.id
    raw.identity_key = identity_key
    raw.identity_payload = json.dumps(identity, ensure_ascii=False, default=str)
    raw.reconciliation_status = "MATCHED"
    raw.reconciliation_score = 100.0
    raw.reconciled_at = now

    global_product.raw_product_count = (
        db.query(RawProduct)
        .filter(RawProduct.global_product_id == global_product.id)
        .count()
    )

    db.flush()
    return raw, global_product, variant
