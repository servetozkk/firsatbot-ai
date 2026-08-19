from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from app.database.models import PriceHistory, ProductDB, ProductGroup, ProductOffer, Store
from app.services.category_scan_manager import CategoryScanManager
from app.services.product_quality_fix_service import suggest_product_fix


@dataclass(slots=True)
class ProductQuality:
    product_id: int
    name: str
    score: int
    level: str
    issues: list[str]
    issue_codes: list[str]
    image_count: int
    ai_score: int
    category: str
    brand: str
    price: float
    updated_at: Any


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _parse_gallery(raw: Any) -> list[str]:
    text_value = str(raw or "").strip()
    if not text_value:
        return []
    try:
        parsed = json.loads(text_value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(parsed, dict):
            result: list[str] = []
            for value in parsed.values():
                if isinstance(value, list):
                    result.extend(str(item).strip() for item in value if str(item).strip())
            return result
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    return [part.strip() for part in re.split(r"[\n,|;]+", text_value) if part.strip()]


def _legacy_gallery_count(product: ProductDB) -> int:
    urls: list[str] = []
    if _has_text(getattr(product, "image", None)):
        urls.append(str(product.image).strip())
    urls.extend(_parse_gallery(getattr(product, "image_gallery", None)))
    return len(dict.fromkeys(urls))


def _normalise_name(value: str) -> str:
    cleaned = unicodedata.normalize("NFKD", value or "")
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch)).casefold()
    cleaned = re.sub(r"\b(trendyol|hepsiburada|amazon|teknosa|n11|cimri|akakce)\b", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    tokens = [token for token in cleaned.split() if len(token) > 1]
    return " ".join(tokens[:20])


def _broken_image(product: ProductDB) -> bool:
    values = []
    if _has_text(getattr(product, "image", None)):
        values.append(str(product.image))
    values.extend(_parse_gallery(getattr(product, "image_gallery", None)))
    if not values:
        return False
    blocked = ("logo", "banner", "placeholder", "no-image", "no_image", "sprite", "favicon", "badge", "icon")
    return all(any(token in value.casefold() for token in blocked) for value in values)


def _suspicious_price(product: ProductDB) -> bool:
    price = float(getattr(product, "price", 0) or 0)
    old_price = float(getattr(product, "old_price", 0) or 0)
    if price <= 0:
        return True
    if old_price > 0 and old_price >= price * 10:
        return True
    if old_price > 0 and price < old_price and ((old_price - price) / old_price) >= 0.96:
        return True
    return False


def _persistent_image_counts(db: Session) -> dict[int, int]:
    try:
        columns = {col["name"] for col in inspect(db.bind).get_columns("product_images")}
        if "product_id" not in columns:
            return {}
        rows = db.execute(text("SELECT product_id, COUNT(*) AS count FROM product_images GROUP BY product_id")).all()
        return {int(row[0]): int(row[1]) for row in rows}
    except Exception:
        return {}


def calculate_product_quality(
    product: ProductDB,
    *,
    history_count: int = 0,
    persistent_image_count: int = 0,
) -> ProductQuality:
    score = 0
    issues: list[str] = []
    issue_codes: list[str] = []
    image_count = max(_legacy_gallery_count(product), int(persistent_image_count or 0))
    broken_image = _broken_image(product)
    suspicious_price = _suspicious_price(product)

    checks = [
        (14, image_count > 0, "Ürün görseli eksik", "missing_image"),
        (6, image_count >= 2, "Galeri yetersiz", "thin_gallery"),
        (5, not broken_image, "Galeri alakasız / bozuk olabilir", "broken_image"),
        (11, _has_text(getattr(product, "brand", None)), "Marka bilgisi eksik", "missing_brand"),
        (11, _has_text(getattr(product, "model", None)) or _has_text(getattr(product, "product_code", None)), "Model / ürün kodu eksik", "missing_model"),
        (11, _has_text(getattr(product, "category", None)), "Kategori bilgisi eksik", "missing_category"),
        (13, _has_text(getattr(product, "specifications", None)), "Teknik özellikler eksik", "missing_specs"),
        (10, not suspicious_price, "Fiyat anormal görünüyor", "suspicious_price"),
        (9, history_count > 0, "Fiyat geçmişi oluşmamış", "missing_history"),
        (10, int(getattr(product, "ai_score", 0) or 0) >= 40, "AI skoru düşük", "low_ai_score"),
    ]

    for points, passed, issue, code in checks:
        if passed:
            score += points
        else:
            issues.append(issue)
            issue_codes.append(code)

    level = "Çok iyi" if score >= 85 else "İyi" if score >= 65 else "Geliştirilmeli" if score >= 45 else "Zayıf"
    return ProductQuality(
        product_id=int(product.id),
        name=product.name,
        score=min(score, 100),
        level=level,
        issues=issues,
        issue_codes=issue_codes,
        image_count=image_count,
        ai_score=int(getattr(product, "ai_score", 0) or 0),
        category=str(getattr(product, "category", "") or ""),
        brand=str(getattr(product, "brand", "") or ""),
        price=float(getattr(product, "price", 0) or 0),
        updated_at=getattr(product, "updated_at", None),
    )


def _active_products_query(db: Session):
    query = db.query(ProductDB)
    if hasattr(ProductDB, "is_deleted"):
        query = query.filter((ProductDB.is_deleted.is_(False)) | (ProductDB.is_deleted.is_(None)))
    return query


def build_data_quality_report(db: Session, limit: int = 500) -> dict[str, Any]:
    products = _active_products_query(db).order_by(ProductDB.updated_at.desc()).all()
    history_counts = dict(
        db.query(PriceHistory.product_id, func.count(PriceHistory.id)).group_by(PriceHistory.product_id).all()
    )
    persistent_counts = _persistent_image_counts(db)

    quality_rows = [
        calculate_product_quality(
            product,
            history_count=int(history_counts.get(product.id, 0)),
            persistent_image_count=int(persistent_counts.get(int(product.id), 0)),
        )
        for product in products
    ]

    average_score = round(sum(row.score for row in quality_rows) / len(quality_rows), 1) if quality_rows else 0
    issue_counter: Counter[str] = Counter()
    issue_code_counter: Counter[str] = Counter()
    for row in quality_rows:
        issue_counter.update(row.issues)
        issue_code_counter.update(row.issue_codes)

    name_groups: dict[str, list[ProductDB]] = defaultdict(list)
    for product in products:
        key = _normalise_name(product.name)
        if key:
            name_groups[key].append(product)
    duplicate_sets = [items for items in name_groups.values() if len(items) > 1]
    duplicate_product_ids = {int(product.id) for group in duplicate_sets for product in group}

    try:
        offer_duplicate_count = (
            db.query(ProductOffer.group_id)
            .group_by(ProductOffer.group_id, ProductOffer.store_id)
            .having(func.count(ProductOffer.id) > 1)
            .count()
        )
    except Exception:
        offer_duplicate_count = 0

    stores = db.query(Store).order_by(Store.name.asc()).all()
    offer_stats = dict(db.query(ProductOffer.store_id, func.count(ProductOffer.id)).group_by(ProductOffer.store_id).all())
    history = CategoryScanManager.get_history(limit=100)
    store_health: dict[str, dict[str, Any]] = defaultdict(lambda: {"success": 0, "failed": 0, "last_scan": None, "last_error": None})
    for task in history:
        finished = task.get("finished_at") or task.get("started_at")
        result = task.get("result") or {}
        rows = result.get("results") if isinstance(result, dict) else None
        if not isinstance(rows, list):
            rows = [task]
        for item in rows:
            category = item.get("category") or {}
            result_item = item.get("result") or item
            label = category.get("source") or category.get("store") or result_item.get("source_site") or task.get("category_name") or "Genel"
            health = store_health[str(label)]
            ok = bool(result_item.get("success", task.get("status") == "completed")) and not item.get("error")
            health["success" if ok else "failed"] += 1
            if finished and (not health["last_scan"] or finished > health["last_scan"]):
                health["last_scan"] = finished
                health["last_error"] = item.get("error") or task.get("error")

    store_rows = []
    for store in stores:
        code = (store.code or store.name).casefold()
        matched = next((value for key, value in store_health.items() if code in key.casefold() or key.casefold() in code), None)
        success = int((matched or {}).get("success", 0))
        failed = int((matched or {}).get("failed", 0))
        total = success + failed
        success_rate = round(success / total * 100, 1) if total else None
        status = "healthy" if success_rate is not None and success_rate >= 90 else "warning" if success_rate is not None and success_rate >= 60 else "unknown" if success_rate is None else "failed"
        store_rows.append({
            "id": store.id,
            "name": store.name,
            "code": store.code,
            "is_active": store.is_active,
            "offer_count": int(offer_stats.get(store.id, 0)),
            "success_rate": success_rate,
            "status": status,
            "last_scan": (matched or {}).get("last_scan"),
            "last_error": (matched or {}).get("last_error"),
        })

    sorted_rows = sorted(quality_rows, key=lambda item: (item.score, item.product_id))
    products_by_id = {int(product.id): product for product in products}
    product_rows = []
    for row in sorted_rows[:limit]:
        product = products_by_id.get(row.product_id)
        suggestion = suggest_product_fix(product) if product is not None else None
        product_rows.append({
            "product_id": row.product_id,
            "name": row.name,
            "score": row.score,
            "level": row.level,
            "issues": row.issues,
            "issue_codes": row.issue_codes,
            "image_count": row.image_count,
            "ai_score": row.ai_score,
            "category": row.category,
            "brand": row.brand,
            "price": row.price,
            "updated_at": row.updated_at,
            "possible_duplicate": row.product_id in duplicate_product_ids,
            "suggestions": suggestion.changes() if suggestion is not None else {},
        })

    healthy_count = sum(1 for row in quality_rows if row.score >= 85)
    attention_count = sum(1 for row in quality_rows if row.score < 65)
    critical_count = sum(1 for row in quality_rows if row.score < 45)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "product_count": len(products),
            "group_count": db.query(ProductGroup).count(),
            "offer_count": db.query(ProductOffer).count(),
            "store_count": len(stores),
            "average_quality_score": average_score,
            "high_quality_count": healthy_count,
            "needs_attention_count": attention_count,
            "critical_count": critical_count,
            "possible_duplicate_count": len(duplicate_sets) + int(offer_duplicate_count),
            "missing_image_count": issue_code_counter.get("missing_image", 0),
            "thin_gallery_count": issue_code_counter.get("thin_gallery", 0),
            "broken_image_count": issue_code_counter.get("broken_image", 0),
            "missing_specs_count": issue_code_counter.get("missing_specs", 0),
            "missing_category_count": issue_code_counter.get("missing_category", 0),
            "missing_brand_count": issue_code_counter.get("missing_brand", 0),
            "missing_model_count": issue_code_counter.get("missing_model", 0),
            "suspicious_price_count": issue_code_counter.get("suspicious_price", 0),
            "missing_history_count": issue_code_counter.get("missing_history", 0),
            "low_ai_score_count": issue_code_counter.get("low_ai_score", 0),
        },
        "issue_counts": dict(issue_code_counter),
        "top_issues": [{"name": name, "count": count} for name, count in issue_counter.most_common(10)],
        "products": product_rows,
        "duplicate_groups": [{
            "key": _normalise_name(group[0].name),
            "count": len(group),
            "products": [{"id": int(product.id), "name": product.name, "price": float(product.price or 0)} for product in group[:5]],
        } for group in duplicate_sets[:20]],
        "stores": store_rows,
        "recent_scans": history[:20],
    }


def write_data_quality_report(db: Session, path: str | Path = "data/data_quality_report.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(build_data_quality_report(db, limit=1000), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return destination.resolve()
