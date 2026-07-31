import math
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse


router = APIRouter(
    prefix="/api/whatsapp",
    tags=["WhatsApp"],
)

DATABASE_PATH = Path("data/products.db")

DEFAULT_MINIMUM_AI_SCORE = 60
DEFAULT_MINIMUM_PRICE_DROP = 10.0
DEFAULT_MINIMUM_HISTORY_COUNT = 3
DEFAULT_MINIMUM_OPPORTUNITY_SCORE = 70
DEFAULT_MINIMUM_AVERAGE_DISCOUNT = 3.0
MAXIMUM_REFERENCE_SPIKE_RATIO = 1.30


def to_number(
    value: Any,
    default: float = 0,
) -> float:
    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def format_price(value: Any) -> str:
    price = to_number(value)

    return (
        f"{price:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def calculate_drop_percentage(
    current_price: float,
    previous_price: float,
) -> float:
    if (
        current_price <= 0
        or previous_price <= 0
        or current_price >= previous_price
    ):
        return 0

    return round(
        (
            (previous_price - current_price)
            / previous_price
        )
        * 100,
        2,
    )


def calculate_below_average_percentage(
    current_price: float,
    average_price: float,
) -> float:
    if (
        current_price <= 0
        or average_price <= 0
        or current_price >= average_price
    ):
        return 0

    return round(
        (
            (average_price - current_price)
            / average_price
        )
        * 100,
        2,
    )


def get_products_and_history():
    if not DATABASE_PATH.exists():
        return [], {}

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        products = connection.execute(
            """
            SELECT
                id,
                name,
                price,
                old_price,
                rating,
                review_count,
                seller,
                url,
                image,
                ai_score,
                last_notified_price
            FROM products
            """
        ).fetchall()

        history_rows = connection.execute(
            """
            SELECT
                id,
                product_id,
                price,
                created_at
            FROM price_history
            WHERE created_at >= datetime('now', '-30 days')
            ORDER BY
                product_id ASC,
                created_at ASC,
                id ASC
            """
        ).fetchall()

    finally:
        connection.close()

    history_map = defaultdict(list)

    for row in history_rows:
        history_map[row["product_id"]].append(
            dict(row)
        )

    return (
        [dict(product) for product in products],
        dict(history_map),
    )


def get_valid_history_prices(
    history: list[dict],
) -> list[float]:
    return [
        to_number(item.get("price"))
        for item in history
        if to_number(item.get("price")) > 0
    ]


def get_previous_price(
    current_price: float,
    historical_prices: list[float],
) -> float:
    if not historical_prices:
        return 0

    for price in reversed(historical_prices):
        if (
            price > 0
            and abs(price - current_price) > 0.01
        ):
            return price

    return 0


def is_fake_price_drop(
    current_price: float,
    previous_price: float,
    historical_prices: list[float],
) -> bool:
    if (
        current_price <= 0
        or previous_price <= 0
        or not historical_prices
    ):
        return True

    stable_prices = [
        price
        for price in historical_prices
        if price > 0
    ]

    if len(stable_prices) < 2:
        return True

    median_price = statistics.median(stable_prices)

    if median_price <= 0:
        return True

    # Önceki fiyat, 30 günlük normal seviyenin çok üstündeyse
    # yapay yükseltilmiş referans fiyat olma ihtimali yüksektir.
    if (
        previous_price
        > median_price * MAXIMUM_REFERENCE_SPIKE_RATIO
    ):
        return True

    # Güncel fiyat medyandan yüksekken yalnızca tek bir şişirilmiş
    # önceki fiyata göre indirim görünüyorsa fırsat sayılmaz.
    if (
        current_price >= median_price
        and previous_price > median_price
    ):
        return True

    return False


def is_already_notified_at_same_price(
    current_price: float,
    last_notified_price: Any,
) -> bool:
    notified_price = to_number(
        last_notified_price
    )

    if notified_price <= 0:
        return False

    return abs(
        current_price - notified_price
    ) < 0.01


def calculate_opportunity_score(
    price_drop: float,
    ai_score: int,
    rating: float,
    review_count: int,
    below_average_percentage: float = 0,
    is_30_day_low: bool = False,
) -> int:
    # İndirim oranı en güçlü faktör.
    price_points = min(
        price_drop * 2.6,
        52,
    )

    # Güncel fiyatın 30 günlük ortalamanın altında olması bonus sağlar.
    average_points = min(
        below_average_percentage * 1.5,
        15,
    )

    ai_points = min(
        max(ai_score, 0) * 0.18,
        18,
    )

    if rating >= 4.7:
        rating_points = 8
    elif rating >= 4.5:
        rating_points = 7
    elif rating >= 4.2:
        rating_points = 5
    elif rating >= 4.0:
        rating_points = 3
    elif rating > 0:
        rating_points = 1
    else:
        rating_points = 0

    if review_count >= 1000:
        review_points = 5
    elif review_count >= 250:
        review_points = 4
    elif review_count >= 50:
        review_points = 3
    elif review_count >= 10:
        review_points = 2
    elif review_count > 0:
        review_points = 1
    else:
        review_points = 0

    low_price_bonus = 5 if is_30_day_low else 0

    penalty = 0

    if rating > 0 and rating < 4.0:
        penalty += 8

    if review_count < 5:
        penalty += 5

    if ai_score < 60:
        penalty += 10

    total = (
        price_points
        + average_points
        + ai_points
        + rating_points
        + review_points
        + low_price_bonus
        - penalty
    )

    return round(
        max(
            0,
            min(total, 100),
        )
    )


def get_opportunity_level(
    opportunity_score: int,
) -> str | None:
    if opportunity_score >= 90:
        return "MEGA FIRSAT"

    if opportunity_score >= 80:
        return "SÜPER FIRSAT"

    if opportunity_score >= 70:
        return "İYİ FIRSAT"

    return None


def create_whatsapp_message(
    product: dict,
) -> str:
    level = (
        product.get("opportunity_level")
        or "İYİ FIRSAT"
    )

    name = product["name"]
    current_price = product["price"]
    previous_price = product["previous_price"]
    price_drop = product["price_drop"]
    price_difference = product["price_difference"]
    rating = product["rating"]
    review_count = product["review_count"]
    seller = product["seller"]
    ai_score = product["ai_score"]
    opportunity_score = product["opportunity_score"]
    below_average_percentage = product[
        "below_average_percentage"
    ]
    url = product["url"]

    lines = [
        level,
        "",
        f"*{name}*",
        "",
        (
            "Yeni fiyat: "
            f"*{format_price(current_price)} TL*"
        ),
        (
            "Önceki fiyat: "
            f"~{format_price(previous_price)} TL~"
        ),
        (
            "İndirim: "
            f"*%{price_drop:.2f}*"
        ),
        (
            "Kazanç: "
            f"*{format_price(price_difference)} TL*"
        ),
        (
            "30 günlük ortalamanın altında: "
            f"*%{below_average_percentage:.2f}*"
        ),
    ]

    if rating > 0:
        rating_line = (
            f"Puan: *{rating:g} / 5*"
        )

        if review_count > 0:
            rating_line += (
                f" ({review_count} değerlendirme)"
            )

        lines.append(rating_line)

    lines.extend(
        [
            f"Satıcı: *{seller}*",
            f"AI puanı: *{ai_score} / 100*",
            (
                "Fırsat skoru: "
                f"*{opportunity_score} / 100*"
            ),
            "",
            "Ürünü incele:",
            url,
            "",
            "Fiyat ve stok anlık olarak değişebilir.",
        ]
    )

    return "\n".join(lines)


def evaluate_product(
    product: dict,
    history: list[dict],
    minimum_ai_score: int,
    minimum_price_drop: float,
    minimum_history_count: int,
    minimum_opportunity_score: int,
    minimum_average_discount: float,
) -> tuple[dict | None, str]:
    product_id = product.get("id")

    current_price = to_number(
        product.get("price")
    )

    if current_price <= 0:
        return None, "invalid_price"

    historical_prices = get_valid_history_prices(
        history
    )

    if len(historical_prices) < minimum_history_count:
        return None, "insufficient_history"

    previous_price = get_previous_price(
        current_price=current_price,
        historical_prices=historical_prices,
    )

    if (
        previous_price <= 0
        or current_price >= previous_price
    ):
        return None, "unchanged"

    if is_already_notified_at_same_price(
        current_price=current_price,
        last_notified_price=product.get(
            "last_notified_price"
        ),
    ):
        return None, "already_notified"

    price_drop = calculate_drop_percentage(
        current_price=current_price,
        previous_price=previous_price,
    )

    if price_drop < minimum_price_drop:
        return None, "weak_drop"

    if is_fake_price_drop(
        current_price=current_price,
        previous_price=previous_price,
        historical_prices=historical_prices,
    ):
        return None, "suspicious_drop"

    average_30_day_price = (
        sum(historical_prices)
        / len(historical_prices)
    )

    below_average_percentage = (
        calculate_below_average_percentage(
            current_price=current_price,
            average_price=average_30_day_price,
        )
    )

    if (
        below_average_percentage
        < minimum_average_discount
    ):
        return None, "not_below_average"

    ai_score = int(
        to_number(
            product.get("ai_score")
        )
    )

    if ai_score < minimum_ai_score:
        return None, "low_ai_score"

    rating = to_number(
        product.get("rating")
    )

    review_count = int(
        to_number(
            product.get("review_count")
        )
    )

    minimum_30_day_price = min(
        historical_prices
    )

    is_30_day_low = (
        current_price
        <= minimum_30_day_price + 0.01
    )

    opportunity_score = (
        calculate_opportunity_score(
            price_drop=price_drop,
            ai_score=ai_score,
            rating=rating,
            review_count=review_count,
            below_average_percentage=(
                below_average_percentage
            ),
            is_30_day_low=is_30_day_low,
        )
    )

    if (
        opportunity_score
        < minimum_opportunity_score
    ):
        return None, "low_opportunity_score"

    opportunity_level = get_opportunity_level(
        opportunity_score
    )

    if opportunity_level is None:
        return None, "low_opportunity_score"

    result = {
        "id": product_id,
        "name": (
            product.get("name")
            or "Ürün"
        ),
        "price": current_price,
        "previous_price": previous_price,
        "price_difference": round(
            previous_price - current_price,
            2,
        ),
        "price_drop": price_drop,
        "history_count": len(
            historical_prices
        ),
        "minimum_30_day_price": round(
            minimum_30_day_price,
            2,
        ),
        "maximum_30_day_price": round(
            max(historical_prices),
            2,
        ),
        "average_30_day_price": round(
            average_30_day_price,
            2,
        ),
        "below_average_percentage": (
            below_average_percentage
        ),
        "is_30_day_low": is_30_day_low,
        "ai_score": ai_score,
        "opportunity_score": (
            opportunity_score
        ),
        "opportunity_level": (
            opportunity_level
        ),
        "rating": rating,
        "review_count": review_count,
        "seller": (
            product.get("seller")
            or "Bilinmiyor"
        ),
        "url": product.get("url") or "",
        "image": product.get("image") or "",
        "last_notified_price": (
            product.get(
                "last_notified_price"
            )
        ),
    }

    result["whatsapp_message"] = (
        create_whatsapp_message(result)
    )

    return result, "ok"


def update_last_notified_price(
    product_id: int,
) -> float:
    if not DATABASE_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Veritabanı bulunamadı.",
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )
    connection.row_factory = sqlite3.Row

    try:
        product = connection.execute(
            """
            SELECT id, price
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()

        if product is None:
            raise HTTPException(
                status_code=404,
                detail="Ürün bulunamadı.",
            )

        current_price = to_number(
            product["price"]
        )

        if current_price <= 0:
            raise HTTPException(
                status_code=400,
                detail="Ürün fiyatı geçersiz.",
            )

        connection.execute(
            """
            UPDATE products
            SET last_notified_price = ?
            WHERE id = ?
            """,
            (
                current_price,
                product_id,
            ),
        )
        connection.commit()

        return current_price

    finally:
        connection.close()


@router.get("/messages")
def get_whatsapp_messages(
    minimum_ai_score: int = Query(
        default=DEFAULT_MINIMUM_AI_SCORE,
        ge=0,
        le=100,
    ),
    minimum_price_drop: float = Query(
        default=DEFAULT_MINIMUM_PRICE_DROP,
        ge=0,
        le=100,
    ),
    minimum_history_count: int = Query(
        default=DEFAULT_MINIMUM_HISTORY_COUNT,
        ge=2,
        le=100,
    ),
    minimum_opportunity_score: int = Query(
        default=DEFAULT_MINIMUM_OPPORTUNITY_SCORE,
        ge=0,
        le=100,
    ),
    minimum_average_discount: float = Query(
        default=DEFAULT_MINIMUM_AVERAGE_DISCOUNT,
        ge=0,
        le=100,
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
):
    products, history_map = (
        get_products_and_history()
    )

    results = []

    counters = {
        "invalid_price_count": 0,
        "insufficient_history_count": 0,
        "unchanged_product_count": 0,
        "weak_drop_count": 0,
        "suspicious_drop_count": 0,
        "not_below_average_count": 0,
        "low_ai_score_count": 0,
        "low_opportunity_score_count": 0,
        "already_notified_count": 0,
    }

    status_counter_map = {
        "invalid_price": "invalid_price_count",
        "insufficient_history": (
            "insufficient_history_count"
        ),
        "unchanged": "unchanged_product_count",
        "weak_drop": "weak_drop_count",
        "suspicious_drop": (
            "suspicious_drop_count"
        ),
        "not_below_average": (
            "not_below_average_count"
        ),
        "low_ai_score": "low_ai_score_count",
        "low_opportunity_score": (
            "low_opportunity_score_count"
        ),
        "already_notified": (
            "already_notified_count"
        ),
    }

    for product in products:
        product_id = product.get("id")

        result, status = evaluate_product(
            product=product,
            history=history_map.get(
                product_id,
                [],
            ),
            minimum_ai_score=minimum_ai_score,
            minimum_price_drop=minimum_price_drop,
            minimum_history_count=(
                minimum_history_count
            ),
            minimum_opportunity_score=(
                minimum_opportunity_score
            ),
            minimum_average_discount=(
                minimum_average_discount
            ),
        )

        if result is None:
            counter_name = status_counter_map.get(
                status
            )

            if counter_name:
                counters[counter_name] += 1

            continue

        results.append(result)

    results.sort(
        key=lambda item: (
            item["opportunity_score"],
            item["price_drop"],
            item["below_average_percentage"],
            item["review_count"],
        ),
        reverse=True,
    )

    selected_results = results[:limit]

    level_counts = {
        "mega_firsat": sum(
            1
            for item in results
            if item["opportunity_level"]
            == "MEGA FIRSAT"
        ),
        "super_firsat": sum(
            1
            for item in results
            if item["opportunity_level"]
            == "SÜPER FIRSAT"
        ),
        "iyi_firsat": sum(
            1
            for item in results
            if item["opportunity_level"]
            == "İYİ FIRSAT"
        ),
    }

    response_data = {
        "success": True,
        "total_product_count": len(products),
        **counters,
        **level_counts,
        "matching_product_count": len(results),
        "returned_count": len(
            selected_results
        ),
        "filters": {
            "minimum_ai_score": (
                minimum_ai_score
            ),
            "minimum_price_drop": (
                minimum_price_drop
            ),
            "minimum_history_count": (
                minimum_history_count
            ),
            "minimum_opportunity_score": (
                minimum_opportunity_score
            ),
            "minimum_average_discount": (
                minimum_average_discount
            ),
            "limit": limit,
        },
        "products": selected_results,
    }

    return JSONResponse(
        content=response_data,
        media_type=(
            "application/json; charset=utf-8"
        ),
    )


@router.post(
    "/mark-notified/{product_id}",
)
def mark_product_as_notified(
    product_id: int,
):
    current_price = update_last_notified_price(
        product_id
    )

    return {
        "success": True,
        "product_id": product_id,
        "last_notified_price": current_price,
        "message": (
            "Ürün paylaşıldı olarak kaydedildi."
        ),
    }