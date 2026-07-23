import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse


router = APIRouter(
    prefix="/api/whatsapp",
    tags=["WhatsApp"],
)

DATABASE_PATH = Path("data/products.db")


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


def calculate_opportunity_score(
    price_drop: float,
    ai_score: int,
    rating: float,
    review_count: int,
) -> int:
    price_points = min(
        price_drop * 4,
        60,
    )

    ai_points = min(
        ai_score * 0.20,
        20,
    )

    rating_points = min(
        rating * 2,
        10,
    )

    if review_count <= 0:
        review_points = 0

    else:
        review_points = min(
            math.log10(review_count + 1) * 3,
            10,
        )

    total = (
        price_points
        + ai_points
        + rating_points
        + review_points
    )

    return round(
        min(total, 100)
    )


def create_whatsapp_message(
    product: dict,
) -> str:
    name = product["name"]
    current_price = product["price"]
    previous_price = product["previous_price"]
    price_drop = product["price_drop"]
    price_difference = product["price_difference"]
    rating = product["rating"]
    review_count = product["review_count"]
    seller = product["seller"]
    opportunity_score = product["opportunity_score"]
    url = product["url"]

    lines = [
        "FIRSAT BULUNDU",
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
            "Fiyat düşüşü: "
            f"*%{price_drop:.2f}*"
        ),
        (
            "Kazanç: "
            f"*{format_price(price_difference)} TL*"
        ),
    ]

    if rating > 0:
        rating_line = (
            f"Puan: *{rating:g} / 5*"
        )

        if review_count > 0:
            rating_line += (
                f" ({review_count} yorum)"
            )

        lines.append(rating_line)

    lines.extend(
        [
            f"Satıcı: {seller}",
            (
                "Fırsat skoru: "
                f"*{opportunity_score} / 100*"
            ),
            "",
            "Ürünü incele:",
            url,
            "",
            "Fiyat ve stok değişebilir.",
        ]
    )

    return "\n".join(lines)


@router.get("/messages")
def get_whatsapp_messages(
    minimum_ai_score: int = Query(
        default=50,
        ge=0,
        le=100,
    ),
    minimum_price_drop: float = Query(
        default=5,
        ge=0,
        le=100,
    ),
    minimum_history_count: int = Query(
        default=2,
        ge=2,
        le=100,
    ),
    minimum_opportunity_score: int = Query(
        default=45,
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

    insufficient_history_count = 0
    unchanged_product_count = 0
    weak_drop_count = 0

    for product in products:
        product_id = product.get("id")

        current_price = to_number(
            product.get("price")
        )

        if current_price <= 0:
            continue

        history = history_map.get(
            product_id,
            [],
        )

        if len(history) < minimum_history_count:
            insufficient_history_count += 1
            continue

        previous_price = to_number(
            history[-2]["price"]
        )

        if (
            previous_price <= 0
            or current_price >= previous_price
        ):
            unchanged_product_count += 1
            continue

        price_drop = calculate_drop_percentage(
            current_price=current_price,
            previous_price=previous_price,
        )

        if price_drop < minimum_price_drop:
            weak_drop_count += 1
            continue

        ai_score = int(
            to_number(
                product.get("ai_score")
            )
        )

        if ai_score < minimum_ai_score:
            continue

        rating = to_number(
            product.get("rating")
        )

        review_count = int(
            to_number(
                product.get("review_count")
            )
        )

        opportunity_score = (
            calculate_opportunity_score(
                price_drop=price_drop,
                ai_score=ai_score,
                rating=rating,
                review_count=review_count,
            )
        )

        if (
            opportunity_score
            < minimum_opportunity_score
        ):
            continue

        historical_prices = [
            to_number(item["price"])
            for item in history
            if to_number(item["price"]) > 0
        ]

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
            "history_count": len(history),
            "minimum_30_day_price": min(
                historical_prices
            ),
            "maximum_30_day_price": max(
                historical_prices
            ),
            "average_30_day_price": round(
                sum(historical_prices)
                / len(historical_prices),
                2,
            ),
            "ai_score": ai_score,
            "opportunity_score":
                opportunity_score,
            "rating": rating,
            "review_count": review_count,
            "seller": (
                product.get("seller")
                or "Bilinmiyor"
            ),
            "url": product.get("url") or "",
            "image": product.get("image"),
        }

        result["whatsapp_message"] = (
            create_whatsapp_message(
                result
            )
        )

        results.append(result)

    results.sort(
        key=lambda item: (
            item["opportunity_score"],
            item["price_drop"],
            item["review_count"],
        ),
        reverse=True,
    )

    selected_results = results[:limit]

    response_data = {
        "success": True,
        "total_product_count": len(products),
        "insufficient_history_count":
            insufficient_history_count,
        "unchanged_product_count":
            unchanged_product_count,
        "weak_drop_count":
            weak_drop_count,
        "matching_product_count": len(results),
        "returned_count": len(
            selected_results
        ),
        "filters": {
            "minimum_ai_score":
                minimum_ai_score,
            "minimum_price_drop":
                minimum_price_drop,
            "minimum_history_count":
                minimum_history_count,
            "minimum_opportunity_score":
                minimum_opportunity_score,
        },
        "products": selected_results,
    }

    return JSONResponse(
        content=response_data,
        media_type=(
            "application/json; charset=utf-8"
        ),
    )