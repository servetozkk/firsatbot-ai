from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from app.database.models import ProductDB, ProductGroup, ProductOffer, Store


STORE_PRIORITY = {
    "turkcellpasaj": 5,
    "teknosa": 1,
    "n11": 2,
    "pazarama": 3,
    "vatan": 4,
    "mediamarkt": 5,
    "trendyol": 6,
    "hepsiburada": 7,
    "amazon": 8,
}


@dataclass(slots=True)
class OfferIssue:
    code: str
    label: str
    severity: str


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _valid_url(value: Any) -> bool:
    try:
        parsed = urlparse(str(value or ""))
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except ValueError:
        return False


def inspect_offer(
    offer: ProductOffer,
    product: ProductDB,
    group: ProductGroup,
    store: Store,
    *,
    now: datetime | None = None,
) -> list[OfferIssue]:
    now = now or datetime.utcnow()
    issues: list[OfferIssue] = []

    if not _text(store.name) or str(store.name).casefold() in {"unknown", "bilinmiyor"}:
        issues.append(OfferIssue("store_name", "Mağaza adı eksik veya bilinmiyor", "critical"))

    if not _text(offer.seller) or str(offer.seller).casefold() in {"unknown", "bilinmiyor"}:
        issues.append(OfferIssue("seller", "Satıcı adı eksik", "warning"))

    if float(offer.current_price or 0) <= 0:
        issues.append(OfferIssue("price", "Geçerli fiyat bulunmuyor", "critical"))

    if not _valid_url(offer.url):
        issues.append(OfferIssue("url", "Teklif bağlantısı geçersiz", "critical"))

    if not _text(offer.availability):
        issues.append(OfferIssue("availability", "Stok durumu eksik", "warning"))

    if offer.shipping_price is None and not _text(offer.shipping_method):
        issues.append(OfferIssue("shipping", "Kargo bilgisi eksik", "warning"))

    if not _text(offer.delivery_text):
        issues.append(OfferIssue("delivery", "Teslimat bilgisi eksik", "info"))

    if not _text(offer.warranty_type):
        issues.append(OfferIssue("warranty", "Garanti bilgisi eksik", "info"))

    if not _text(offer.installment_text):
        issues.append(OfferIssue("installment", "Taksit bilgisi eksik", "info"))

    if not _text(offer.campaign_text):
        issues.append(OfferIssue("campaign", "Kampanya bilgisi eksik", "info"))

    if not _text(product.image) and not _text(group.image):
        issues.append(OfferIssue("image", "Ürün görseli eksik", "warning"))

    if not _text(product.brand) and not _text(group.brand):
        issues.append(OfferIssue("brand", "Marka bilgisi eksik", "warning"))

    if not _text(product.model) and not _text(group.model):
        issues.append(OfferIssue("model", "Model bilgisi eksik", "warning"))

    if float(offer.match_score or 0) <= 0:
        issues.append(OfferIssue("match_score", "Eşleşme güven puanı yok", "warning"))
    elif float(offer.match_score or 0) < 70:
        issues.append(OfferIssue("match_score_low", "Eşleşme güveni düşük", "critical"))

    checked_at = offer.last_checked_at or offer.updated_at or offer.created_at
    if not checked_at:
        issues.append(OfferIssue("last_checked", "Son kontrol zamanı yok", "warning"))
    elif checked_at < now - timedelta(hours=48):
        issues.append(OfferIssue("stale", "Teklif 48 saatten eski", "critical"))
    elif checked_at < now - timedelta(hours=24):
        issues.append(OfferIssue("aging", "Teklif 24 saatten eski", "warning"))

    if str(offer.lifecycle_status or "ACTIVE") in {"MISSING", "ARCHIVED"}:
        issues.append(OfferIssue("lifecycle", f"Teklif durumu: {offer.lifecycle_status}", "warning"))

    if offer.is_hidden:
        issues.append(OfferIssue("hidden", "Teklif kullanıcıdan gizli", "info"))

    return issues


def completeness_score(issues: list[OfferIssue]) -> int:
    penalty = 0
    for issue in issues:
        penalty += {"critical": 18, "warning": 8, "info": 3}.get(issue.severity, 3)
    return max(0, 100 - penalty)


def build_validation_report(db, *, selected_store: str = "", limit: int = 500) -> dict[str, Any]:
    query = (
        db.query(ProductOffer, ProductDB, ProductGroup, Store)
        .join(ProductDB, ProductDB.id == ProductOffer.product_id)
        .join(ProductGroup, ProductGroup.id == ProductOffer.group_id)
        .join(Store, Store.id == ProductOffer.store_id)
    )

    if selected_store:
        query = query.filter(Store.code == selected_store)

    rows = query.order_by(ProductOffer.updated_at.desc()).limit(limit).all()
    now = datetime.utcnow()

    store_buckets: dict[int, dict[str, Any]] = {}
    detailed_rows: list[dict[str, Any]] = []
    issue_counter: Counter[str] = Counter()

    for offer, product, group, store in rows:
        issues = inspect_offer(offer, product, group, store, now=now)
        score = completeness_score(issues)
        issue_counter.update(issue.code for issue in issues)

        bucket = store_buckets.setdefault(
            store.id,
            {
                "store": store,
                "offer_count": 0,
                "scores": [],
                "critical": 0,
                "warning": 0,
                "info": 0,
                "fields": Counter(),
                "complete_offers": 0,
            },
        )
        bucket["offer_count"] += 1
        bucket["scores"].append(score)
        for issue in issues:
            bucket[issue.severity] += 1
            bucket["fields"][issue.code] += 1
        if score >= 85:
            bucket["complete_offers"] += 1

        detailed_rows.append(
            {
                "offer": offer,
                "product": product,
                "group": group,
                "store": store,
                "issues": [asdict(issue) for issue in issues],
                "score": score,
                "critical_count": sum(1 for issue in issues if issue.severity == "critical"),
                "warning_count": sum(1 for issue in issues if issue.severity == "warning"),
            }
        )

    store_rows = []
    for bucket in store_buckets.values():
        scores = bucket.pop("scores")
        fields = bucket.pop("fields")
        offer_count = bucket["offer_count"]
        store = bucket["store"]
        store_rows.append(
            {
                **bucket,
                "score": round(sum(scores) / len(scores), 1) if scores else 0,
                "coverage_percent": round(bucket["complete_offers"] / offer_count * 100, 1) if offer_count else 0,
                "top_issues": fields.most_common(5),
                "priority": STORE_PRIORITY.get(str(store.code or "").casefold(), 99),
            }
        )

    store_rows.sort(key=lambda row: (row["priority"], row["score"], row["store"].name.casefold()))
    detailed_rows.sort(
        key=lambda row: (
            -row["critical_count"],
            -row["warning_count"],
            row["score"],
            str(row["store"].name).casefold(),
        )
    )

    total_offers = len(detailed_rows)
    average_score = round(
        sum(row["score"] for row in detailed_rows) / total_offers, 1
    ) if total_offers else 0

    return {
        "stores": store_rows,
        "rows": detailed_rows,
        "summary": {
            "offer_count": total_offers,
            "store_count": len(store_rows),
            "average_score": average_score,
            "critical_offers": sum(1 for row in detailed_rows if row["critical_count"] > 0),
            "ready_offers": sum(1 for row in detailed_rows if row["score"] >= 85),
        },
        "issue_counts": issue_counter.most_common(),
    }
