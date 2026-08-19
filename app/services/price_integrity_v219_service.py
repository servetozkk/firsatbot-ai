from __future__ import annotations

from dataclasses import dataclass
import re
from datetime import datetime
from statistics import median
from typing import Any

from app.database.database import SessionLocal
from app.database.models import GlobalOffer, GlobalProduct, GlobalOfferPriceHistory, ProductOffer
from app.services.price_integrity_math_v219 import decide_price_integrity

ENGINE_VERSION = "23.15.0"
QUARANTINED = "QUARANTINED"
ACTIVE = "ACTIVE"

# Conservative thresholds: a price is quarantined only when there is strong
# catalogue evidence. A single competitor is not enough by itself.
LOW_RATIO = 0.35
HIGH_RATIO = 2.75
MIN_PEER_COUNT = 2
HISTORY_WINDOW = 20


@dataclass(frozen=True, slots=True)
class PriceIntegrityVerdict:
    trusted: bool
    status: str
    reason: str
    reference_price: float | None
    ratio: float | None
    peer_count: int
    evidence_prices: tuple[float, ...]


def _valid_price(value: Any) -> float | None:
    try:
        price = float(value or 0)
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None


def _peer_prices(db, *, global_product_id: int, store_code: str, exclude_offer_id: int | None = None) -> list[float]:
    query = db.query(GlobalOffer).filter(
        GlobalOffer.global_product_id == int(global_product_id),
        GlobalOffer.is_active.is_(True),
        GlobalOffer.is_hidden.is_(False),
        GlobalOffer.lifecycle_status == ACTIVE,
        GlobalOffer.current_price > 0,
        GlobalOffer.store_code != str(store_code or "").casefold(),
    )
    if exclude_offer_id is not None:
        query = query.filter(GlobalOffer.id != int(exclude_offer_id))
    return [float(row.current_price) for row in query.all() if _valid_price(row.current_price)]


def _history_prices(db, *, global_product_id: int, store_code: str) -> list[float]:
    rows = (
        db.query(GlobalOfferPriceHistory)
        .filter(
            GlobalOfferPriceHistory.global_product_id == int(global_product_id),
            GlobalOfferPriceHistory.store_code == str(store_code or "").casefold(),
            GlobalOfferPriceHistory.price > 0,
        )
        .order_by(GlobalOfferPriceHistory.recorded_at.desc(), GlobalOfferPriceHistory.id.desc())
        .limit(HISTORY_WINDOW)
        .all()
    )
    return [float(row.price) for row in rows if _valid_price(row.price)]


ACCESSORY_LOW_RATIO_V237 = 0.55
PHONE_LOW_RATIO_V237 = 0.55
CATEGORY_MIN_PEER_COUNT_V237 = 2


def _fold_v237(value: Any) -> str:
    return (
        str(value or "")
        .casefold()
        .translate(str.maketrans({"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}))
    )


def _category_leaf_v237(product: GlobalProduct | None) -> str:
    if product is None:
        return ""
    raw = str(getattr(product, "category", "") or "")
    parts = [
        _fold_v237(part).strip()
        for part in re.split(r"[>›»|]+", raw)
        if str(part).strip()
    ]
    return parts[-1] if parts else _fold_v237(raw).strip()


def _product_kind_contract_v2315(product: GlobalProduct | None) -> tuple[str, str]:
    """V23.15 strong type/category-first product-kind contract.

    Returns (kind, subkind). Strong product-type/category evidence always wins
    over broad brand-family prefixes such as ``redmi`` or ``galaxy``.
    """
    if product is None:
        return "generic", "generic"

    leaf = _category_leaf_v237(product)
    category = _fold_v237(getattr(product, "category", ""))
    family = _fold_v237(getattr(product, "family", ""))
    model = _fold_v237(getattr(product, "model", ""))
    name = _fold_v237(getattr(product, "canonical_name", ""))
    identity = _fold_v237(getattr(product, "identity_source", ""))
    detail = " ".join((category, leaf, family, model, name, identity))

    # Strong explicit product-type/category routing comes first. This prevents
    # e.g. Xiaomi/Redmi powerbanks from being classified as phones merely
    # because their canonical family starts with "redmi ".
    if any(x in detail for x in ("powerbank", "power bank", "tasinabilir sarj", "tasınabilir sarj")):
        return "accessory", "powerbank"
    if (
        ("aku" in detail or "akü" in str(getattr(product, "category", "") or "").casefold())
        and any(x in detail for x in ("atesleyici", "takviye", "jump starter"))
    ) or ("lastik sisirici" in detail and "psi" in detail):
        return "accessory", "jump_starter_inflator"
    if any(x in detail for x in ("oda kokusu", "cubuklu oda kokusu", "reed diffuser", "room fragrance")):
        return "generic", "room_fragrance"
    if any(x in detail for x in ("parfum", "parfüm", " eau de parfum", " eau de toilette", " edp ", " edt ")):
        return "generic", "perfume"

    if any(x in detail for x in ("macbook", "ideapad", "thinkpad", "notebook", "laptop")):
        return "laptop", "laptop"
    if any(x in detail for x in ("galaxy tab ", "ipad ", " tablet")):
        return "tablet", "tablet"
    if any(x in detail for x in ("apple watch", "galaxy watch", "redmi watch", "akilli saat", "smartwatch", "giyilebilir")):
        return "wearable", "smartwatch"
    if any(x in detail for x in ("redmi buds", "galaxy buds", "airpods", "earbuds", "kulaklik", "headphone", "bluetooth kulak")):
        return "audio/headphone", "headphone"

    # Explicit phone category wins over broad family inference.
    if any(x in category for x in ("cep telefonu", "akilli telefon", "smartphone")):
        return "phone", "phone"

    # Generic accessories after strong special cases, before phone-family
    # inference, so "redmi ... powerbank" can never become phone.
    if any(x in detail for x in ("sarj", "charger", "adapt", "adapter", "usb-c", "usb c", "kablo", "kilif", "ekran koruyucu")):
        return "accessory", "accessory"

    if family.startswith(("iphone ", "redmi ", "poco ", "galaxy a", "galaxy s", "fold ", "flip ", "xiaomi ")):
        return "phone", "phone"
    return "generic", "generic"


def _product_kind_v237(product: GlobalProduct | None) -> str:
    return _product_kind_contract_v2315(product)[0]


def _product_subkind_v2315(product: GlobalProduct | None) -> str:
    return _product_kind_contract_v2315(product)[1]


def _category_low_price_verdict_v237(
    *,
    db,
    global_product_id: int,
    candidate_price: float,
    evidence_prices: list[float],
) -> PriceIntegrityVerdict | None:
    product = db.get(GlobalProduct, int(global_product_id))
    kind = _product_kind_v237(product)
    if kind not in {"accessory", "phone"}:
        return None

    valid_evidence = sorted(
        float(price)
        for price in evidence_prices
        if _valid_price(price) is not None
    )
    if len(valid_evidence) < CATEGORY_MIN_PEER_COUNT_V237:
        return None

    reference = float(median(valid_evidence))
    if reference <= 0:
        return None
    ratio = float(candidate_price) / reference
    threshold = (
        ACCESSORY_LOW_RATIO_V237
        if kind == "accessory"
        else PHONE_LOW_RATIO_V237
    )
    if ratio >= threshold:
        return None

    label = "aksesuar" if kind == "accessory" else "telefon"
    return PriceIntegrityVerdict(
        False,
        QUARANTINED,
        (
            f"V23.7 {label} fiyat anomalisi: fiyat emsal medyanın "
            f"%{ratio * 100:.1f} seviyesinde."
        ),
        reference,
        ratio,
        len(valid_evidence),
        tuple(valid_evidence),
    )



def evaluate_price_candidate(
    *,
    db,
    global_product_id: int,
    store_code: str,
    candidate_price: float,
    existing_offer: GlobalOffer | None = None,
) -> PriceIntegrityVerdict:
    price = _valid_price(candidate_price)
    if price is None:
        return PriceIntegrityVerdict(False, QUARANTINED, "Geçersiz veya sıfır fiyat.", None, None, 0, ())

    peers = _peer_prices(
        db,
        global_product_id=global_product_id,
        store_code=store_code,
        exclude_offer_id=(existing_offer.id if existing_offer is not None else None),
    )
    history = _history_prices(db, global_product_id=global_product_id, store_code=store_code)

    # Strong evidence is primarily cross-store. Own history helps only when it
    # is consistent with at least one peer, preventing one bad historical value
    # from poisoning the decision.
    evidence = list(peers)
    if len(peers) >= 1 and history:
        hist_ref = float(median(history))
        peer_ref = float(median(peers))
        if 0.60 <= (hist_ref / peer_ref) <= 1.67:
            evidence.append(hist_ref)

    category_verdict = _category_low_price_verdict_v237(
        db=db,
        global_product_id=int(global_product_id),
        candidate_price=price,
        evidence_prices=evidence,
    )
    if category_verdict is not None:
        return category_verdict

    decision = decide_price_integrity(
        candidate_price=price,
        evidence_prices=evidence,
    )
    return PriceIntegrityVerdict(
        decision.trusted,
        decision.status,
        decision.reason,
        decision.reference_price,
        decision.ratio,
        decision.peer_count,
        decision.evidence_prices,
    )


def _quarantine_offer(db, offer: GlobalOffer, verdict: PriceIntegrityVerdict) -> None:
    offer.is_active = False
    offer.is_hidden = True
    offer.lifecycle_status = QUARANTINED
    offer.duplicate_reason = (
        "PRICE_INTEGRITY_V237 | " + verdict.reason +
        (f" | reference={verdict.reference_price:.2f}" if verdict.reference_price else "") +
        (f" | ratio={verdict.ratio:.4f}" if verdict.ratio is not None else "")
    )
    offer.updated_at = datetime.utcnow()
    if offer.legacy_offer_id:
        legacy = db.get(ProductOffer, int(offer.legacy_offer_id))
        if legacy is not None:
            legacy.is_active = False
            legacy.is_hidden = True
            legacy.lifecycle_status = QUARANTINED
            legacy.updated_at = datetime.utcnow()




def _activate_offer_v237(db, offer: GlobalOffer) -> None:
    offer.is_active = True
    offer.is_hidden = False
    offer.lifecycle_status = ACTIVE
    if str(offer.duplicate_reason or "").startswith("PRICE_INTEGRITY_"):
        offer.duplicate_reason = None
    offer.updated_at = datetime.utcnow()
    if offer.legacy_offer_id:
        legacy = db.get(ProductOffer, int(offer.legacy_offer_id))
        if legacy is not None:
            legacy.is_active = True
            legacy.is_hidden = False
            legacy.lifecycle_status = ACTIVE
            if str(getattr(legacy, "duplicate_reason", "") or "").startswith("PRICE_INTEGRITY_"):
                legacy.duplicate_reason = None
            legacy.updated_at = datetime.utcnow()


def quarantine_offer(*, db, offer: GlobalOffer, verdict: PriceIntegrityVerdict) -> None:
    _quarantine_offer(db, offer, verdict)
    _refresh_count(db, int(offer.global_product_id))


def quarantine_legacy_offer(legacy_offer: ProductOffer | None, reason: str) -> None:
    if legacy_offer is None:
        return
    legacy_offer.is_active = False
    legacy_offer.is_hidden = True
    legacy_offer.lifecycle_status = QUARANTINED
    legacy_offer.updated_at = datetime.utcnow()


def _refresh_count(db, global_product_id: int) -> None:
    product = db.get(GlobalProduct, int(global_product_id))
    if product is None:
        return
    product.active_offer_count = db.query(GlobalOffer).filter(
        GlobalOffer.global_product_id == int(global_product_id),
        GlobalOffer.is_active.is_(True),
        GlobalOffer.is_hidden.is_(False),
        GlobalOffer.lifecycle_status == ACTIVE,
        GlobalOffer.current_price > 0,
    ).count()
    product.updated_at = datetime.utcnow()


def audit_product_prices(*, db, global_product_id: int) -> dict[str, Any]:
    rows = (
        db.query(GlobalOffer)
        .filter(
            GlobalOffer.global_product_id == int(global_product_id),
            GlobalOffer.current_price > 0,
        )
        .order_by(GlobalOffer.id.asc())
        .all()
    )
    quarantined: list[dict[str, Any]] = []
    trusted: list[dict[str, Any]] = []
    recovered: list[dict[str, Any]] = []

    active_rows = [
        row for row in rows
        if bool(row.is_active)
        and not bool(row.is_hidden)
        and str(row.lifecycle_status or ACTIVE).upper() == ACTIVE
    ]
    recoverable_rows = [
        row for row in rows
        if str(row.lifecycle_status or "").upper() == QUARANTINED
        and str(row.duplicate_reason or "").startswith("PRICE_INTEGRITY_")
    ]

    original = {
        int(row.id): (
            bool(row.is_active),
            bool(row.is_hidden),
            str(row.lifecycle_status or ACTIVE),
        )
        for row in active_rows
    }

    # Active set is evaluated as one batch. Decisions are applied afterwards,
    # so one early quarantine cannot remove peer evidence for later rows.
    active_decisions: list[tuple[GlobalOffer, PriceIntegrityVerdict, dict[str, Any]]] = []
    for row in active_rows:
        verdict = evaluate_price_candidate(
            db=db,
            global_product_id=int(global_product_id),
            store_code=str(row.store_code or "").casefold(),
            candidate_price=float(row.current_price or 0),
            existing_offer=row,
        )
        item = {
            "offer_id": int(row.id),
            "store_code": row.store_code,
            "seller": row.seller,
            "price": float(row.current_price or 0),
            "status": verdict.status,
            "trusted": verdict.trusted,
            "reason": verdict.reason,
            "reference_price": verdict.reference_price,
            "ratio": verdict.ratio,
            "peer_count": verdict.peer_count,
        }
        active_decisions.append((row, verdict, item))
        if verdict.trusted:
            trusted.append(item)
        else:
            quarantined.append(item)

    for row in active_rows:
        was_active, was_hidden, lifecycle = original[int(row.id)]
        row.is_active = was_active
        row.is_hidden = was_hidden
        row.lifecycle_status = lifecycle

    for row, verdict, _item in active_decisions:
        if not verdict.trusted:
            _quarantine_offer(db, row, verdict)

    # V23.7 recovery: older price-integrity quarantine rows are not permanent.
    # Re-evaluate against the currently trusted peer set and reactivate when the
    # new category-aware policy says the price is legitimate.
    db.flush()
    for row in recoverable_rows:
        verdict = evaluate_price_candidate(
            db=db,
            global_product_id=int(global_product_id),
            store_code=str(row.store_code or "").casefold(),
            candidate_price=float(row.current_price or 0),
            existing_offer=row,
        )
        item = {
            "offer_id": int(row.id),
            "store_code": row.store_code,
            "seller": row.seller,
            "price": float(row.current_price or 0),
            "status": verdict.status,
            "trusted": verdict.trusted,
            "reason": verdict.reason,
            "reference_price": verdict.reference_price,
            "ratio": verdict.ratio,
            "peer_count": verdict.peer_count,
        }
        if verdict.trusted:
            _activate_offer_v237(db, row)
            item["recovered_from_quarantine"] = True
            recovered.append(item)
            trusted.append(item)
        else:
            _quarantine_offer(db, row, verdict)
            # Avoid duplicate reporting if row was already in active decisions.
            if not any(int(x["offer_id"]) == int(row.id) for x in quarantined):
                quarantined.append(item)

    _refresh_count(db, int(global_product_id))
    return {
        "engine": "FIRSATAI_PRICE_INTEGRITY_QUARANTINE_ENGINE",
        "engine_version": ENGINE_VERSION,
        "global_product_id": int(global_product_id),
        "checked_offer_count": len(active_rows) + len(recoverable_rows),
        "active_checked_offer_count": len(active_rows),
        "recoverable_checked_offer_count": len(recoverable_rows),
        "trusted_offer_count": len(trusted),
        "quarantined_offer_count": len(quarantined),
        "recovered_offer_count": len(recovered),
        "quarantined": quarantined,
        "recovered": recovered,
        "trusted": trusted,
        "product_kind": _product_kind_v237(db.get(GlobalProduct, int(global_product_id))),
        "product_subkind": _product_subkind_v2315(db.get(GlobalProduct, int(global_product_id))),
    }


def audit_all_prices(*, db=None) -> dict[str, Any]:
    owns_db = db is None
    if owns_db:
        db = SessionLocal()
    try:
        product_ids = [row[0] for row in db.query(GlobalOffer.global_product_id).distinct().all()]
        results = []
        total_quarantined = 0
        for product_id in product_ids:
            result = audit_product_prices(db=db, global_product_id=int(product_id))
            if result["checked_offer_count"] >= 2 or result["quarantined_offer_count"]:
                results.append(result)
            total_quarantined += int(result["quarantined_offer_count"])
        db.commit()
        return {
            "engine": "FIRSATAI_PRICE_INTEGRITY_QUARANTINE_ENGINE",
            "engine_version": ENGINE_VERSION,
            "product_count": len(product_ids),
            "quarantined_offer_count": total_quarantined,
            "results": results,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_db:
            db.close()


def get_price_integrity_status(*, db, global_product_id: int) -> dict[str, Any]:
    rows = (
        db.query(GlobalOffer)
        .filter(GlobalOffer.global_product_id == int(global_product_id))
        .order_by(GlobalOffer.store_code.asc(), GlobalOffer.id.asc())
        .all()
    )
    offers = []
    for row in rows:
        offers.append({
            "offer_id": int(row.id),
            "store_code": row.store_code,
            "seller": row.seller,
            "price": float(row.current_price or 0),
            "is_active": bool(row.is_active),
            "is_hidden": bool(row.is_hidden),
            "lifecycle_status": row.lifecycle_status,
            "quarantine_reason": row.duplicate_reason if str(row.lifecycle_status or "").upper() == QUARANTINED else None,
            "served_to_users": bool(row.is_active) and not bool(row.is_hidden) and str(row.lifecycle_status or ACTIVE).upper() == ACTIVE,
        })
    served = [x for x in offers if x["served_to_users"] and float(x["price"] or 0) > 0]
    served_prices = [float(x["price"]) for x in served]
    return {
        "engine": "FIRSATAI_PRICE_INTEGRITY_QUARANTINE_ENGINE",
        "engine_version": ENGINE_VERSION,
        "global_product_id": int(global_product_id),
        "product_kind": _product_kind_v237(db.get(GlobalProduct, int(global_product_id))),
        "product_subkind": _product_subkind_v2315(db.get(GlobalProduct, int(global_product_id))),
        "offer_count": len(offers),
        "served_offer_count": len(served),
        "served_store_count": len({str(x["store_code"] or "") for x in served}),
        "served_store_codes": sorted({str(x["store_code"] or "") for x in served}),
        "served_best_price": min(served_prices) if served_prices else None,
        "served_highest_price": max(served_prices) if served_prices else None,
        "quarantined_offer_count": sum(1 for x in offers if x["lifecycle_status"] == QUARANTINED),
        "offers": offers,
    }
