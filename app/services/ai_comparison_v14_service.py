from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path("data/products.db")


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _bounded(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def _money(value: Any) -> str:
    try:
        return (
            f"{float(value):,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
            + " TL"
        )
    except (TypeError, ValueError):
        return "Fiyat yok"


def _availability_ok(value: Any) -> bool:
    text = str(value or "").casefold()
    return not any(x in text for x in ("tükendi", "stokta yok", "out of stock"))


def analyze_global_product(product_id: int) -> dict[str, Any]:
    with _connect() as con:
        product = con.execute(
            """
            SELECT id,canonical_name,normalized_brand,family,model,variant,
                   ram_gb,storage_gb,model_code,identity_source,
                   raw_product_count,active_offer_count,status
            FROM global_products
            WHERE id=?
            """,
            (int(product_id),),
        ).fetchone()

        if product is None:
            return {
                "available": False,
                "quality_score": 0,
                "quality_level": "Yetersiz",
                "warnings": ["Global ürün bulunamadı."],
                "advantages": [],
            }

        offers = con.execute(
            """
            SELECT id,store_code,current_price,old_price,shipping_price,
                   availability,warranty_type,campaign_text,
                   installment_text,is_official_seller,is_active,is_hidden,
                   lifecycle_status,last_seen_at
            FROM global_offers
            WHERE global_product_id=?
              AND is_active=1
              AND is_hidden=0
              AND current_price>0
            ORDER BY current_price
            """,
            (int(product_id),),
        ).fetchall()

        variants = con.execute(
            """
            SELECT color,network,model_code
            FROM global_product_variants
            WHERE global_product_id=?
            """,
            (int(product_id),),
        ).fetchall()

        history = con.execute(
            """
            SELECT price,total_price,recorded_at
            FROM global_offer_price_history
            WHERE global_product_id=?
            ORDER BY recorded_at DESC
            LIMIT 180
            """,
            (int(product_id),),
        ).fetchall()

    p = dict(product)
    offer_rows = [dict(x) for x in offers]
    prices = [float(x["current_price"]) for x in offer_rows]
    store_count = len({x["store_code"] for x in offer_rows})
    official_count = sum(1 for x in offer_rows if x["is_official_seller"])
    stock_count = sum(1 for x in offer_rows if _availability_ok(x["availability"]))
    campaign_count = sum(1 for x in offer_rows if x["campaign_text"])
    warranty_count = sum(1 for x in offer_rows if x["warranty_type"])
    installment_count = sum(1 for x in offer_rows if x["installment_text"])

    identity_fields = [
        p.get("normalized_brand"),
        p.get("family"),
        p.get("model"),
        p.get("ram_gb"),
        p.get("storage_gb"),
        p.get("model_code"),
    ]
    identity_completeness = sum(v not in (None, "", 0) for v in identity_fields) / len(identity_fields)

    warnings: list[str] = []
    advantages: list[str] = []
    quality_reasons: list[str] = []

    if not prices:
        warnings.append("Aktif fiyat teklifi bulunmuyor.")
        return {
            "available": True,
            "quality_score": 20,
            "quality_level": "Düşük",
            "confidence_score": 20,
            "warnings": warnings,
            "advantages": advantages,
            "quality_reasons": ["Ürün kimliği var ancak aktif fiyat verisi yok."],
            "technical_summary": [],
            "market_summary": {
                "store_count": 0,
                "offer_count": 0,
                "best_price": None,
            },
        }

    best = min(prices)
    highest = max(prices)
    median = statistics_median(prices)
    spread_percent = ((highest - best) / highest * 100) if highest > 0 else 0

    # Kimlik ve veri güveni. Bu puan yapay zekâ tahmini değil;
    # ürün alanlarının ve mağaza kanıtlarının deterministik kalite puanıdır.
    score = 25
    score += identity_completeness * 35
    score += min(store_count, 5) * 6
    score += min(len(offer_rows), 8) * 2
    score += 6 if p.get("identity_source") else 0
    score += 5 if p.get("model_code") else 0
    score += 4 if p.get("ram_gb") or p.get("storage_gb") else 0
    score -= 12 if len(variants) > 5 and not p.get("model_code") else 0

    if store_count == 1:
        warnings.append("Fiyat yalnızca tek mağazadan doğrulanıyor.")
    else:
        quality_reasons.append(f"{store_count} farklı mağazada aktif fiyat kanıtı var.")

    if identity_completeness < 0.5:
        warnings.append("Ürün kimliğinde marka/model/varyant alanları eksik.")
    else:
        quality_reasons.append("Marka, model ve varyant alanlarının çoğu dolu.")

    if len(variants) > 4 and not p.get("model_code"):
        warnings.append("Çok sayıda varyant var; model kodu eksik olduğu için manuel kontrol önerilir.")

    if spread_percent > 60:
        warnings.append(
            "Mağazalar arasındaki fiyat farkı çok yüksek; yanlış varyant eşleşmesi ihtimali kontrol edilmeli."
        )
    elif spread_percent >= 5:
        advantages.append(
            f"En pahalı teklife göre {_money(highest - best)} (%{spread_percent:.2f}) tasarruf var."
        )

    if official_count:
        advantages.append(f"{official_count} resmi satıcı teklifi bulunuyor.")
    if campaign_count:
        advantages.append(f"{campaign_count} teklifte kampanya bilgisi var.")
    if installment_count:
        advantages.append(f"{installment_count} teklifte taksit bilgisi var.")
    if warranty_count:
        advantages.append(f"{warranty_count} teklifte garanti bilgisi var.")
    if stock_count == 0:
        warnings.append("Aktif teklifler stokta görünmüyor.")

    technical_summary: list[str] = []
    if p.get("ram_gb"):
        technical_summary.append(f"{p['ram_gb']} GB RAM")
    if p.get("storage_gb"):
        technical_summary.append(f"{p['storage_gb']} GB depolama")
    if p.get("model_code"):
        technical_summary.append(f"Model kodu: {p['model_code']}")
    networks = sorted({str(x["network"]) for x in variants if x["network"]})
    colors = sorted({str(x["color"]) for x in variants if x["color"]})
    if networks:
        technical_summary.append("Ağ: " + ", ".join(networks[:4]))
    if colors:
        technical_summary.append(f"{len(colors)} renk varyantı")

    history_prices = [
        float(x["total_price"] if x["total_price"] is not None else x["price"])
        for x in history
        if (x["total_price"] is not None or x["price"] is not None)
    ]
    price_insight = {
        "history_points": len(history_prices),
        "historical_low": min(history_prices) if history_prices else None,
        "historical_low_text": _money(min(history_prices)) if history_prices else None,
        "current_vs_low_percent": None,
    }
    if history_prices:
        historical_low = min(history_prices)
        if historical_low > 0:
            price_insight["current_vs_low_percent"] = round(
                (best - historical_low) / historical_low * 100,
                2,
            )
            if best <= historical_low:
                advantages.append("Güncel en düşük fiyat, kayıtlı fiyat geçmişinin en düşük seviyesinde.")
            elif price_insight["current_vs_low_percent"] <= 5:
                advantages.append("Güncel fiyat, kayıtlı tarihi dip seviyeye çok yakın.")

    quality_score = _bounded(score)
    if quality_score >= 85:
        quality_level = "Çok yüksek"
    elif quality_score >= 70:
        quality_level = "Yüksek"
    elif quality_score >= 50:
        quality_level = "Orta"
    else:
        quality_level = "Düşük"

    return {
        "available": True,
        "engine_version": "14.5.0",
        "quality_score": quality_score,
        "confidence_score": quality_score,
        "quality_level": quality_level,
        "warnings": warnings,
        "advantages": advantages,
        "quality_reasons": quality_reasons,
        "technical_summary": technical_summary,
        "market_summary": {
            "store_count": store_count,
            "offer_count": len(offer_rows),
            "official_seller_count": official_count,
            "stock_offer_count": stock_count,
            "best_price": best,
            "best_price_text": _money(best),
            "highest_price": highest,
            "highest_price_text": _money(highest),
            "median_price": median,
            "median_price_text": _money(median),
            "spread_percent": round(spread_percent, 2),
        },
        "price_insight": price_insight,
    }


def statistics_median(values: list[float]) -> float:
    ordered = sorted(values)
    size = len(ordered)
    middle = size // 2
    if size % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def data_quality_status(limit: int = 500) -> dict[str, Any]:
    with _connect() as con:
        ids = [
            int(r["id"])
            for r in con.execute(
                """
                SELECT id
                FROM global_products
                WHERE status='ACTIVE'
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (max(1, min(int(limit), 2000)),),
            ).fetchall()
        ]

    results = [analyze_global_product(product_id) for product_id in ids]
    scored = [x for x in results if x.get("available")]
    distribution = {
        "very_high": sum(1 for x in scored if x["quality_score"] >= 85),
        "high": sum(1 for x in scored if 70 <= x["quality_score"] < 85),
        "medium": sum(1 for x in scored if 50 <= x["quality_score"] < 70),
        "low": sum(1 for x in scored if x["quality_score"] < 50),
    }
    warning_total = sum(len(x.get("warnings", [])) for x in scored)
    suspicious = [
        {
            "product_id": product_id,
            "quality_score": result["quality_score"],
            "warnings": result.get("warnings", []),
        }
        for product_id, result in zip(ids, results)
        if result.get("warnings")
    ][:50]

    average = round(
        sum(x["quality_score"] for x in scored) / len(scored),
        2,
    ) if scored else 0

    return {
        "engine_version": "14.5.0",
        "status": "AI_COMPARISON_READY",
        "scanned_products": len(scored),
        "average_quality_score": average,
        "warning_total": warning_total,
        "distribution": distribution,
        "suspicious_products": suspicious,
    }
