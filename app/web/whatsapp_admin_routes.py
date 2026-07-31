from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import (
    HTMLResponse,
    Response,
)
from fastapi.templating import Jinja2Templates

from app.services.deal_image_generator import create_deal_image
from app.web.whatsapp_routes import (
    calculate_drop_percentage,
    calculate_opportunity_score,
    get_products_and_history,
    to_number,
)


router = APIRouter(
    prefix="/admin",
    tags=["Admin WhatsApp"],
)

BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


def format_tr_money(value: Any) -> str:
    """Sayıyı Türkçe para biçiminde gösterir."""
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0

    formatted = f"{number:,.2f}"

    return (
        formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def parse_int_query(
    value: str | None,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    try:
        if value is None or value.strip() == "":
            number = default
        else:
            number = int(value)
    except (TypeError, ValueError, AttributeError):
        number = default

    if minimum is not None:
        number = max(number, minimum)

    if maximum is not None:
        number = min(number, maximum)

    return number


def parse_float_query(
    value: str | None,
    default: float,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        if value is None or value.strip() == "":
            number = default
        else:
            number = float(value.replace(",", "."))
    except (TypeError, ValueError, AttributeError):
        number = default

    if minimum is not None:
        number = max(number, minimum)

    if maximum is not None:
        number = min(number, maximum)

    return number


def build_whatsapp_message(
    product: dict[str, Any],
) -> str:
    opportunity_score = int(
        to_number(product.get("opportunity_score"))
    )
    ai_score = int(
        to_number(product.get("ai_score"))
    )

    name = product.get("name") or "Ürün"
    seller = product.get("seller") or "Belirtilmedi"
    url = product.get("url") or ""

    price = to_number(product.get("price"))
    previous_price = to_number(product.get("previous_price"))
    price_difference = to_number(product.get("price_difference"))
    price_drop = to_number(product.get("price_drop"))

    rating = to_number(product.get("rating"))
    review_count = int(
        to_number(product.get("review_count"))
    )

    if opportunity_score >= 95:
        title = "🚨🔥 MEGA FIRSAT 🔥🚨"
        urgency = "⏰ Bu fiyat uzun süre kalmayabilir!"
    elif opportunity_score >= 90:
        title = "🔥 SÜPER FIRSAT 🔥"
        urgency = "⚡ Fırsatı kaçırmadan incele!"
    elif opportunity_score >= 80:
        title = "💥 GÜNÜN FIRSATI 💥"
        urgency = "👀 Avantajlı fiyatı hemen incele!"
    else:
        title = "✅ İYİ FİYAT"
        urgency = "🛒 Ürünü ve güncel fiyatı incele!"

    formatted_reviews = (
        f"{review_count:,}"
        .replace(",", ".")
    )

    formatted_drop = (
        f"{price_drop:.2f}"
        .replace(".", ",")
    )

    return f"""{title}

📦 *{name}*

💰 Yeni fiyat: *{format_tr_money(price)} TL*
❌ Eski fiyat: ~{format_tr_money(previous_price)} TL~

📉 İndirim: *%{formatted_drop}*
💸 Kazanç: *{format_tr_money(price_difference)} TL*

⭐ Puan: *{rating:g} / 5*
📝 Değerlendirme: *{formatted_reviews}*

🏪 Satıcı: *{seller}*

🤖 AI puanı: *{ai_score} / 100*
🚀 Fırsat skoru: *{opportunity_score} / 100*

━━━━━━━━━━━━━━

{urgency}

🛍️ *Ürünü İncele:*
{url}

⚠️ Fiyat ve stok anlık olarak değişebilir."""


def get_product_history(
    history_map: dict,
    product_id: Any,
) -> list[dict]:
    possible_ids = [
        product_id,
        str(product_id),
    ]

    try:
        possible_ids.append(int(product_id))
    except (TypeError, ValueError):
        pass

    for possible_id in possible_ids:
        history = history_map.get(possible_id)

        if history is not None:
            return list(history)

    return []


def sort_history(
    history: list[dict],
) -> list[dict]:
    if not history:
        return []

    possible_date_fields = (
        "created_at",
        "recorded_at",
        "checked_at",
        "date",
        "timestamp",
    )

    date_field = next(
        (
            field
            for field in possible_date_fields
            if any(item.get(field) for item in history)
        ),
        None,
    )

    if date_field is None:
        return list(history)

    return sorted(
        history,
        key=lambda item: str(
            item.get(date_field) or ""
        ),
    )


def build_product_result(
    product: dict,
    history: list[dict],
) -> tuple[dict | None, str]:
    product_id = product.get("id")
    current_price = to_number(product.get("price"))

    if current_price <= 0:
        return None, "invalid_price"

    ordered_history = sort_history(history)

    historical_prices = [
        to_number(item.get("price"))
        for item in ordered_history
        if to_number(item.get("price")) > 0
    ]

    if len(historical_prices) < 2:
        return None, "insufficient_history"

    last_history_price = historical_prices[-1]

    if abs(last_history_price - current_price) < 0.0001:
        previous_price = historical_prices[-2]
    else:
        previous_price = last_history_price

    if previous_price <= 0 or current_price >= previous_price:
        return None, "no_price_drop"

    price_drop = calculate_drop_percentage(
        current_price=current_price,
        previous_price=previous_price,
    )

    ai_score = int(
        to_number(product.get("ai_score"))
    )
    rating = to_number(product.get("rating"))
    review_count = int(
        to_number(product.get("review_count"))
    )

    opportunity_score = calculate_opportunity_score(
        price_drop=price_drop,
        ai_score=ai_score,
        rating=rating,
        review_count=review_count,
    )

    result = {
        "id": product_id,
        "name": product.get("name") or "Ürün",
        "price": current_price,
        "previous_price": previous_price,
        "price_difference": round(
            previous_price - current_price,
            2,
        ),
        "price_drop": round(
            to_number(price_drop),
            2,
        ),
        "history_count": len(historical_prices),
        "minimum_30_day_price": min(historical_prices),
        "maximum_30_day_price": max(historical_prices),
        "average_30_day_price": round(
            sum(historical_prices) / len(historical_prices),
            2,
        ),
        "ai_score": ai_score,
        "opportunity_score": int(
            to_number(opportunity_score)
        ),
        "rating": rating,
        "review_count": review_count,
        "seller": product.get("seller") or "Bilinmiyor",
        "url": product.get("url") or "",
        "image": product.get("image") or "",
        "last_notified_price": product.get(
            "last_notified_price"
        ),
    }

    result["whatsapp_message"] = build_whatsapp_message(result)
    return result, "ok"


def load_products_and_history():
    data = get_products_and_history()

    if (
        not isinstance(data, tuple)
        or len(data) != 2
    ):
        raise HTTPException(
            status_code=500,
            detail="Ürün ve fiyat geçmişi verileri alınamadı.",
        )

    products, history_map = data

    return (
        list(products or []),
        dict(history_map or {}),
    )


@router.get(
    "/whatsapp",
    response_class=HTMLResponse,
)
def whatsapp_dashboard(
    request: Request,
    minimum_ai_score: str | None = Query(default=None),
    minimum_price_drop: str | None = Query(default=None),
    minimum_history_count: str | None = Query(default=None),
    minimum_opportunity_score: str | None = Query(default=None),
    limit: str | None = Query(default=None),
):
    parsed_minimum_ai_score = parse_int_query(
        value=minimum_ai_score,
        default=0,
        minimum=0,
        maximum=100,
    )

    parsed_minimum_price_drop = parse_float_query(
        value=minimum_price_drop,
        default=0.0,
        minimum=0.0,
        maximum=100.0,
    )

    parsed_minimum_history_count = parse_int_query(
        value=minimum_history_count,
        default=2,
        minimum=0,
    )

    parsed_minimum_opportunity_score = parse_int_query(
        value=minimum_opportunity_score,
        default=0,
        minimum=0,
        maximum=100,
    )

    parsed_limit = parse_int_query(
        value=limit,
        default=50,
        minimum=1,
        maximum=500,
    )

    products, history_map = load_products_and_history()

    opportunities = []

    insufficient_history_count = 0
    no_price_drop_count = 0
    invalid_price_count = 0

    for product in products:
        product_id = product.get("id")

        history = get_product_history(
            history_map=history_map,
            product_id=product_id,
        )

        result, status = build_product_result(
            product=product,
            history=history,
        )

        if status == "insufficient_history":
            insufficient_history_count += 1
            continue

        if status == "no_price_drop":
            no_price_drop_count += 1
            continue

        if status == "invalid_price":
            invalid_price_count += 1
            continue

        if result is None:
            continue

        if result["ai_score"] < parsed_minimum_ai_score:
            continue

        if result["price_drop"] < parsed_minimum_price_drop:
            continue

        if result["history_count"] < parsed_minimum_history_count:
            continue

        if (
            result["opportunity_score"]
            < parsed_minimum_opportunity_score
        ):
            continue

        opportunities.append(result)

    opportunities.sort(
        key=lambda item: (
            item["opportunity_score"],
            item["price_drop"],
        ),
        reverse=True,
    )

    opportunities = opportunities[:parsed_limit]

    context = {
        "request": request,
        "products": opportunities,
        "opportunities": opportunities,
        "results": opportunities,
        "total_products": len(products),
        "total_product_count": len(products),
        "product_count": len(products),
        "found_opportunities": len(opportunities),
        "found_count": len(opportunities),
        "opportunity_count": len(opportunities),
        "insufficient_history": insufficient_history_count,
        "insufficient_history_count": insufficient_history_count,
        "no_price_drop": no_price_drop_count,
        "no_price_drop_count": no_price_drop_count,
        "invalid_price_count": invalid_price_count,
        "minimum_ai_score": parsed_minimum_ai_score,
        "min_ai_score": parsed_minimum_ai_score,
        "minimum_price_drop": parsed_minimum_price_drop,
        "minimum_drop": parsed_minimum_price_drop,
        "min_drop": parsed_minimum_price_drop,
        "minimum_history_count": parsed_minimum_history_count,
        "minimum_history": parsed_minimum_history_count,
        "min_history": parsed_minimum_history_count,
        "minimum_opportunity_score": (
            parsed_minimum_opportunity_score
        ),
        "minimum_score": parsed_minimum_opportunity_score,
        "limit": parsed_limit,
    }

    return templates.TemplateResponse(
        request=request,
        name="whatsapp_dashboard.html",
        context=context,
    )


@router.get(
    "/whatsapp/deal-image/{product_id}",
)
def whatsapp_deal_image(
    product_id: int,
    download: bool = Query(default=False),
):
    products, history_map = load_products_and_history()

    selected_product = next(
        (
            product
            for product in products
            if int(product.get("id") or 0) == product_id
        ),
        None,
    )

    if selected_product is None:
        raise HTTPException(
            status_code=404,
            detail="Ürün bulunamadı.",
        )

    history = get_product_history(
        history_map=history_map,
        product_id=product_id,
    )

    result, status = build_product_result(
        product=selected_product,
        history=history,
    )

    if result is None:
        error_messages = {
            "insufficient_history": (
                "Ürünün yeterli fiyat geçmişi bulunmuyor."
            ),
            "no_price_drop": (
                "Ürünün fiyatı düşmemiş."
            ),
            "invalid_price": (
                "Ürünün güncel fiyatı geçersiz."
            ),
        }

        raise HTTPException(
            status_code=404,
            detail=error_messages.get(
                status,
                "Bu ürün için geçerli fırsat bulunamadı.",
            ),
        )

    image_bytes = create_deal_image(result)

    if hasattr(image_bytes, "getvalue"):
        image_bytes = image_bytes.getvalue()

    if not isinstance(
        image_bytes,
        (bytes, bytearray),
    ):
        raise HTTPException(
            status_code=500,
            detail="Fırsat görseli oluşturulamadı.",
        )

    headers = {}

    if download:
        headers["Content-Disposition"] = (
            f'attachment; filename="firsat-{product_id}.png"'
        )

    return Response(
        content=bytes(image_bytes),
        media_type="image/png",
        headers=headers,
    )