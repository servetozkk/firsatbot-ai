from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from app.database.models import ProductDB, ProductGroup, ProductOffer, Store
from app.services.offer_validation_service import inspect_offer, completeness_score


def _safe_age_hours(value: datetime | None, now: datetime) -> float | None:
    if not value:
        return None
    return max((now - value).total_seconds() / 3600, 0.0)


def _status_bucket(score: int, critical_count: int) -> str:
    if critical_count > 0 or score < 55:
        return "broken"
    if score < 85:
        return "incomplete"
    return "ready"


def build_offer_health_dashboard(db, *, selected_store: str = "") -> dict[str, Any]:
    query = (
        db.query(ProductOffer, ProductDB, ProductGroup, Store)
        .join(ProductDB, ProductDB.id == ProductOffer.product_id)
        .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        .join(Store, Store.id == ProductOffer.store_id)
    )
    if selected_store:
        query = query.filter(Store.code == selected_store)

    rows = query.all()
    now = datetime.utcnow()

    stores: dict[int, dict[str, Any]] = {}
    global_fields: Counter[str] = Counter()
    recent_broken = 0
    total_ready = total_incomplete = total_broken = 0

    for offer, product, group, store in rows:
        issues = inspect_offer(offer, product, group, store, now=now)
        score = completeness_score(issues)
        critical_count = sum(1 for issue in issues if issue.severity == "critical")
        bucket = _status_bucket(score, critical_count)

        if bucket == "ready":
            total_ready += 1
        elif bucket == "incomplete":
            total_incomplete += 1
        else:
            total_broken += 1

        if bucket == "broken":
            updated = offer.updated_at or offer.last_checked_at or offer.created_at
            if updated and updated >= now - timedelta(hours=24):
                recent_broken += 1

        store_row = stores.setdefault(
            store.id,
            {
                "store": store,
                "offers": 0,
                "ready": 0,
                "incomplete": 0,
                "broken": 0,
                "scores": [],
                "match_scores": [],
                "ages": [],
                "field_counts": Counter(),
                "active": 0,
                "archived": 0,
                "hidden": 0,
                "free_shipping": 0,
                "official_seller": 0,
                "with_delivery": 0,
                "with_warranty": 0,
                "with_campaign": 0,
                "with_installment": 0,
                "with_image": 0,
            },
        )
        store_row["offers"] += 1
        store_row[bucket] += 1
        store_row["scores"].append(score)

        if float(offer.match_score or 0) > 0:
            store_row["match_scores"].append(float(offer.match_score))

        checked = offer.last_checked_at or offer.updated_at or offer.created_at
        age = _safe_age_hours(checked, now)
        if age is not None:
            store_row["ages"].append(age)

        lifecycle = str(offer.lifecycle_status or "ACTIVE")
        if lifecycle in {"ACTIVE", "UPDATED", "OUT_OF_STOCK"} and offer.is_active:
            store_row["active"] += 1
        if lifecycle == "ARCHIVED":
            store_row["archived"] += 1
        if offer.is_hidden:
            store_row["hidden"] += 1

        if offer.shipping_price == 0:
            store_row["free_shipping"] += 1
        if offer.is_official_seller:
            store_row["official_seller"] += 1
        if offer.delivery_text:
            store_row["with_delivery"] += 1
        if offer.warranty_type:
            store_row["with_warranty"] += 1
        if offer.campaign_text:
            store_row["with_campaign"] += 1
        if offer.installment_text:
            store_row["with_installment"] += 1
        if product.image or group.image:
            store_row["with_image"] += 1

        for issue in issues:
            store_row["field_counts"][issue.code] += 1
            global_fields[issue.code] += 1

    store_rows: list[dict[str, Any]] = []
    for row in stores.values():
        count = row["offers"] or 1
        scores = row.pop("scores")
        matches = row.pop("match_scores")
        ages = row.pop("ages")
        fields = row.pop("field_counts")

        score = round(mean(scores), 1) if scores else 0.0
        avg_match = round(mean(matches), 1) if matches else 0.0
        avg_age = round(mean(ages), 1) if ages else None
        latest_age = round(min(ages), 1) if ages else None

        row.update(
            {
                "score": score,
                "avg_match": avg_match,
                "avg_age_hours": avg_age,
                "latest_age_hours": latest_age,
                "success_percent": round(row["ready"] / count * 100, 1),
                "problem_percent": round(row["broken"] / count * 100, 1),
                "active_percent": round(row["active"] / count * 100, 1),
                "delivery_coverage": round(row["with_delivery"] / count * 100, 1),
                "warranty_coverage": round(row["with_warranty"] / count * 100, 1),
                "shipping_coverage": round(
                    (count - fields.get("shipping", 0)) / count * 100, 1
                ),
                "seller_coverage": round(
                    (count - fields.get("seller", 0)) / count * 100, 1
                ),
                "image_coverage": round(row["with_image"] / count * 100, 1),
                "top_issues": fields.most_common(6),
            }
        )
        store_rows.append(row)

    store_rows.sort(
        key=lambda row: (
            -row["broken"],
            row["score"],
            str(row["store"].name).casefold(),
        )
    )

    total = len(rows)
    return {
        "stores": store_rows,
        "summary": {
            "offer_count": total,
            "store_count": len(store_rows),
            "ready": total_ready,
            "incomplete": total_incomplete,
            "broken": total_broken,
            "ready_percent": round(total_ready / total * 100, 1) if total else 0,
            "recent_broken": recent_broken,
        },
        "top_missing_fields": global_fields.most_common(10),
    }
