from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from app.database.models import ProductDB, ProductOffer, ProductGroup
from app.models.product import Product
from app.services.data_integrity_service import stable_product_key
from app.services.product_identity_service import ProductIdentityService


@dataclass(slots=True)
class IdentityAuditRow:
    product_id: int
    name: str
    image: str | None
    brand: str
    model: str
    category: str
    identity_key: str
    identity_source: str
    stable_key: str
    confidence: int
    status: str
    warnings: list[str]
    attributes: dict[str, Any]
    group_id: int | None = None
    group_name: str | None = None
    store_count: int = 0


def _to_product(row: ProductDB) -> Product:
    return Product(
        name=row.name or "",
        price=float(row.price or 0),
        old_price=row.old_price,
        rating=row.rating,
        review_count=row.review_count,
        seller=row.seller or "",
        url=row.url or "",
        image=row.image,
        image_gallery=row.image_gallery,
        brand=row.brand,
        model=row.model,
        category=row.category,
        description=row.description,
        specifications=row.specifications,
        stock_status=row.stock_status,
        source_site=row.source_site,
        product_code=row.product_code,
    )


def _score_identity(info: dict[str, Any], row: ProductDB) -> tuple[int, list[str]]:
    score = 18
    warnings: list[str] = []
    brand = str(info.get("normalized_brand") or "").strip()
    family = str(info.get("family") or "").strip()
    variant = str(info.get("variant") or "").strip()
    model_code = str(info.get("model_code") or "").strip()
    storage = info.get("storage_gb")
    ram = info.get("ram_gb")

    if brand:
        score += 22
    else:
        warnings.append("Marka belirlenemedi")
    if family:
        score += 28
    else:
        warnings.append("Model ailesi zayıf")
    if variant:
        score += 7
    if model_code:
        score += 10
    if storage is not None:
        score += 8
    if ram is not None:
        score += 5
    if not str(row.category or "").strip():
        warnings.append("Kategori eksik")
    if not str(row.product_code or "").strip() and not model_code:
        warnings.append("Ürün/model kodu yok")
    if len(family.split()) > 5:
        score -= 12
        warnings.append("Model adı fazla genel")
    score = max(0, min(100, score))
    status = "strong" if score >= 80 else "review" if score >= 58 else "weak"
    return score, warnings


def audit_products(session, products: Iterable[ProductDB]) -> list[IdentityAuditRow]:
    rows = list(products)
    product_ids = [int(row.id) for row in rows]
    offer_map: dict[int, tuple[int, str, int]] = {}
    if product_ids:
        offer_rows = (
            session.query(ProductOffer, ProductGroup)
            .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
            .filter(ProductOffer.product_id.in_(product_ids))
            .all()
        )
        group_store_counts: dict[int, set[int]] = defaultdict(set)
        for offer, _group in offer_rows:
            group_store_counts[int(offer.group_id)].add(int(offer.store_id))
        for offer, group in offer_rows:
            offer_map[int(offer.product_id)] = (
                int(group.id),
                str(group.canonical_name or ""),
                len(group_store_counts[int(group.id)]),
            )

    result: list[IdentityAuditRow] = []
    for row in rows:
        product = _to_product(row)
        info = ProductIdentityService.explain(product)
        confidence, warnings = _score_identity(info, row)
        identity_key = str(info.get("identity_key") or "")
        stable = stable_product_key(
            identity_key=identity_key,
            product_code=row.product_code,
            url=row.url,
            name=row.name,
        )
        group_id, group_name, store_count = offer_map.get(int(row.id), (None, None, 0))
        status = "strong" if confidence >= 80 else "review" if confidence >= 58 else "weak"
        result.append(IdentityAuditRow(
            product_id=int(row.id),
            name=str(row.name or "İsimsiz ürün"),
            image=row.image,
            brand=str(info.get("normalized_brand") or ""),
            model=str(info.get("normalized_model") or ""),
            category=str(row.category or ""),
            identity_key=identity_key,
            identity_source=str(info.get("identity_source") or ""),
            stable_key=stable,
            confidence=confidence,
            status=status,
            warnings=warnings,
            attributes={
                "variant": info.get("variant"),
                "ram_gb": info.get("ram_gb"),
                "storage_gb": info.get("storage_gb"),
                "screen_inch": info.get("screen_inch"),
                "color": info.get("color"),
                "network": info.get("network"),
                "model_code": info.get("model_code"),
            },
            group_id=group_id,
            group_name=group_name,
            store_count=store_count,
        ))
    return result


def build_duplicate_clusters(rows: Iterable[IdentityAuditRow]) -> list[dict[str, Any]]:
    grouped: dict[str, list[IdentityAuditRow]] = defaultdict(list)
    for row in rows:
        if row.identity_key:
            grouped[row.identity_key].append(row)
    clusters = []
    for identity_key, items in grouped.items():
        if len(items) < 2:
            continue
        group_ids = {item.group_id for item in items if item.group_id is not None}
        clusters.append({
            "identity_key": identity_key,
            "items": items,
            "count": len(items),
            "group_count": len(group_ids),
            "needs_merge": len(group_ids) > 1,
            "average_confidence": round(sum(item.confidence for item in items) / len(items)),
        })
    clusters.sort(key=lambda item: (not item["needs_merge"], -item["count"], -item["average_confidence"]))
    return clusters


def apply_identity_updates(session, product_ids: list[int]) -> dict[str, int]:
    if not product_ids:
        return {"updated": 0, "brand_filled": 0, "model_filled": 0, "stable_key_updated": 0}
    products = (
        session.query(ProductDB)
        .filter(ProductDB.id.in_(product_ids), ProductDB.is_deleted.is_(False))
        .all()
    )
    stats = {"updated": 0, "brand_filled": 0, "model_filled": 0, "stable_key_updated": 0}
    for row in products:
        product = _to_product(row)
        info = ProductIdentityService.explain(product)
        changed = False
        normalized_brand = str(info.get("normalized_brand") or "").strip()
        normalized_model = str(info.get("normalized_model") or "").strip()
        if not str(row.brand or "").strip() and normalized_brand:
            row.brand = normalized_brand.title()
            stats["brand_filled"] += 1
            changed = True
        if not str(row.model or "").strip() and normalized_model:
            row.model = normalized_model
            stats["model_filled"] += 1
            changed = True
        new_stable_key = stable_product_key(
            identity_key=str(info.get("identity_key") or ""),
            product_code=row.product_code,
            url=row.url,
            name=row.name,
        )
        if row.stable_key != new_stable_key:
            row.stable_key = new_stable_key
            stats["stable_key_updated"] += 1
            changed = True
        if changed:
            stats["updated"] += 1
    session.commit()
    return stats
