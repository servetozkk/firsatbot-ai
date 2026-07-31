from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from urllib.parse import urlencode

from app.services.category_catalog import (
    build_category_catalog,
    build_featured_categories,
)

from app.database.database import SessionLocal
from app.database.models import (
    PriceHistory,
    ProductDB,
    ProductGroup,
    ProductOffer,
    Store,
)


router = APIRouter()


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BASE_DIR / "app" / "templates"



CATEGORY_PRESENTATION = {
    "laptop": {
        "icon": "💻",
        "description": "Oyun, iş ve günlük kullanım için dizüstü bilgisayarlar",
    },
    "notebook": {
        "icon": "💻",
        "description": "Taşınabilir bilgisayar modelleri ve güncel fırsatlar",
    },
    "telefon": {
        "icon": "📱",
        "description": "Akıllı telefon modelleri ve mağaza fiyatları",
    },
    "akilli telefon": {
        "icon": "📱",
        "description": "Akıllı telefon modelleri ve mağaza fiyatları",
    },
    "monitor": {
        "icon": "🖥️",
        "description": "Ofis, oyun ve profesyonel kullanım monitörleri",
    },
    "televizyon": {
        "icon": "📺",
        "description": "Farklı ekran boyutlarında televizyon fırsatları",
    },
    "kulaklik": {
        "icon": "🎧",
        "description": "Kablosuz, oyuncu ve günlük kullanım kulaklıkları",
    },
    "tablet": {
        "icon": "▣",
        "description": "Eğitim, iş ve eğlence için tablet modelleri",
    },
    "klavye": {
        "icon": "⌨️",
        "description": "Mekanik, oyuncu ve ofis klavyeleri",
    },
    "mouse": {
        "icon": "🖱️",
        "description": "Oyuncu ve günlük kullanım fareleri",
    },
    "ekran karti": {
        "icon": "🎮",
        "description": "Oyun ve profesyonel kullanım ekran kartları",
    },
    "islemci": {
        "icon": "⚙️",
        "description": "Masaüstü sistemler için işlemci modelleri",
    },
    "ssd": {
        "icon": "💾",
        "description": "Hızlı ve yüksek kapasiteli depolama çözümleri",
    },
    "beyaz esya": {
        "icon": "🏠",
        "description": "Ev ihtiyaçları için beyaz eşya fırsatları",
    },
}


def _normalize_category_name(value: str) -> str:
    translation = str.maketrans(
        {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
            "Ç": "c",
            "Ğ": "g",
            "İ": "i",
            "Ö": "o",
            "Ş": "s",
            "Ü": "u",
        }
    )
    return " ".join(
        str(value or "")
        .translate(translation)
        .casefold()
        .split()
    )


def _category_presentation(category_name: str) -> dict[str, str]:
    normalized_name = _normalize_category_name(category_name)

    for keyword, presentation in CATEGORY_PRESENTATION.items():
        if keyword in normalized_name:
            return presentation

    return {
        "icon": "🛍️",
        "description": f"{category_name} ürünlerini ve güncel fiyatlarını inceleyin",
    }


def build_home_categories(db) -> list[dict[str, object]]:
    """
    ProductGroup kayıtlarından ana sayfa kategori kartlarını üretir.

    Kategoriler ürün sayısına göre sıralanır. Yeni kategori kayıtları
    veritabanına eklendiğinde ana sayfada otomatik görünür.
    """

    category_rows = (
        db.query(
            ProductGroup.category,
            func.count(ProductGroup.id).label("product_count"),
            func.max(ProductGroup.image).label("sample_image"),
        )
        .filter(
            ProductGroup.category.isnot(None),
            ProductGroup.category != "",
        )
        .group_by(ProductGroup.category)
        .order_by(
            func.count(ProductGroup.id).desc(),
            ProductGroup.category.asc(),
        )
        .all()
    )

    categories: list[dict[str, object]] = []

    for category_name, product_count, sample_image in category_rows:
        clean_name = str(category_name or "").strip()

        if not clean_name:
            continue

        presentation = _category_presentation(clean_name)
        query_string = urlencode({"category": clean_name})

        categories.append(
            {
                "name": clean_name,
                "product_count": int(product_count or 0),
                "sample_image": sample_image,
                "icon": presentation["icon"],
                "description": presentation["description"],
                "url": f"/karsilastir?{query_string}",
            }
        )

    return categories


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _calculate_discount_percent(product) -> int:
    price = _safe_float(getattr(product, "price", 0))
    old_price = _safe_float(getattr(product, "old_price", 0))

    if old_price <= 0 or price <= 0 or old_price <= price:
        return 0

    return max(
        0,
        min(
            99,
            round(((old_price - price) / old_price) * 100),
        ),
    )


def _product_card(product) -> dict[str, object]:
    price = _safe_float(getattr(product, "price", 0))
    old_price = _safe_float(getattr(product, "old_price", 0))
    discount_percent = _calculate_discount_percent(product)
    saving_amount = (
        max(0.0, old_price - price)
        if old_price > price
        else 0.0
    )

    search_name = str(getattr(product, "name", "") or "").strip()
    detail_url = (
        "/karsilastir?"
        + urlencode({"search": search_name})
    )

    return {
        "id": getattr(product, "id", None),
        "name": search_name or "İsimsiz ürün",
        "price": price,
        "old_price": old_price,
        "discount_percent": discount_percent,
        "saving_amount": saving_amount,
        "rating": _safe_float(getattr(product, "rating", 0)),
        "review_count": int(getattr(product, "review_count", 0) or 0),
        "seller": str(getattr(product, "seller", "") or "Mağaza"),
        "image": getattr(product, "image", None),
        "ai_score": int(getattr(product, "ai_score", 0) or 0),
        "category": str(getattr(product, "category", "") or "Diğer"),
        "stock_status": str(
            getattr(product, "stock_status", "") or "Bilinmiyor"
        ),
        "detail_url": detail_url,
        "store_url": getattr(product, "url", None),
        "created_at": getattr(product, "created_at", None),
        "last_price_change": getattr(
            product,
            "last_price_change",
            None,
        ),
    }


def _take_unique_products(
    products: list,
    *,
    sort_key,
    limit: int = 8,
    predicate=None,
) -> list[dict[str, object]]:
    candidates = [
        product
        for product in products
        if predicate is None or predicate(product)
    ]
    candidates.sort(key=sort_key, reverse=True)

    result: list[dict[str, object]] = []
    seen_names: set[str] = set()

    for product in candidates:
        card = _product_card(product)
        normalized_name = " ".join(
            str(card["name"]).casefold().split()
        )

        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)
        result.append(card)

        if len(result) >= limit:
            break

    return result


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
)


@router.get("/")
def home(request: Request):
    """Offer Engine verilerini kullanan müşteri ana sayfası."""
    db = SessionLocal()

    try:
        groups = (
            db.query(ProductGroup)
            .order_by(ProductGroup.updated_at.desc(), ProductGroup.id.desc())
            .all()
        )

        database_category_rows = (
            db.query(
                ProductGroup.category,
                func.count(ProductGroup.id),
            )
            .filter(
                ProductGroup.category.isnot(None),
                ProductGroup.category != "",
            )
            .group_by(ProductGroup.category)
            .all()
        )
        category_catalog = build_category_catalog(database_category_rows)
        featured_categories = build_featured_categories(category_catalog)
        main_categories = [
            {
                "name": category["name"],
                "slug": category["slug"],
                "icon": category["icon"],
                "product_count": category["product_count"],
            }
            for category in category_catalog
        ]

        cards: list[dict[str, object]] = []
        for group in groups:
            offers = (
                db.query(ProductOffer, Store)
                .join(Store, Store.id == ProductOffer.store_id)
                .filter(ProductOffer.group_id == group.id)
                .order_by(ProductOffer.current_price.asc())
                .all()
            )
            if not offers:
                continue

            available_rows = [
                (offer, store)
                for offer, store in offers
                if str(offer.availability or "").casefold()
                not in {"stokta yok", "out of stock", "unavailable"}
            ] or offers

            prices = [float(offer.current_price or 0) for offer, _ in available_rows if float(offer.current_price or 0) > 0]
            if not prices:
                continue

            best_offer, best_store = min(
                available_rows,
                key=lambda row: float(row[0].current_price or float("inf")),
            )
            best_price = float(best_offer.current_price or 0)
            highest_price = max(prices)
            saving_amount = max(0.0, highest_price - best_price)
            saving_percent = round((saving_amount / highest_price) * 100, 2) if highest_price else 0.0

            old_price = float(best_offer.old_price or 0)
            direct_discount = (
                round(((old_price - best_price) / old_price) * 100, 2)
                if old_price > best_price > 0
                else 0.0
            )
            displayed_discount = max(saving_percent, direct_discount)

            cards.append(
                {
                    "id": group.id,
                    "name": group.canonical_name,
                    "price": best_price,
                    "old_price": old_price if old_price > best_price else highest_price,
                    "discount_percent": int(round(displayed_discount)),
                    "saving_amount": round(max(saving_amount, old_price - best_price if old_price > best_price else 0), 2),
                    "rating": float(best_offer.rating or 0),
                    "review_count": int(best_offer.review_count or 0),
                    "seller": best_store.name or best_offer.seller or "Mağaza",
                    "image": group.image,
                    "ai_score": min(100, int(round(55 + displayed_discount * 3))) if displayed_discount > 0 else 50,
                    "category": group.category or "Diğer",
                    "stock_status": best_offer.availability or "Bilinmiyor",
                    "detail_url": f"/karsilastir/{group.group_key}",
                    "store_url": best_offer.url,
                    "created_at": group.created_at,
                    "last_price_change": best_offer.updated_at,
                    "offer_count": len(available_rows),
                }
            )

        total_products = len(cards)
        grouped_product_count = len(groups)
        prices = [float(card["price"]) for card in cards if float(card["price"]) > 0]
        average_price = round(sum(prices) / len(prices), 2) if prices else 0
        highest_price = max(prices, default=0)
        lowest_price = min(prices, default=0)

        best_deals = sorted(
            [card for card in cards if int(card["discount_percent"]) > 0],
            key=lambda card: (int(card["discount_percent"]), float(card["saving_amount"])),
            reverse=True,
        )[:8]
        top_scored_products = sorted(
            cards,
            key=lambda card: (int(card["ai_score"]), int(card["discount_percent"])),
            reverse=True,
        )[:8]
        price_drop_products = sorted(
            [card for card in cards if float(card["old_price"] or 0) > float(card["price"] or 0)],
            key=lambda card: (int(card["discount_percent"]), card["last_price_change"] or card["created_at"]),
            reverse=True,
        )[:8]
        newest_products = sorted(
            cards,
            key=lambda card: card["created_at"] or card["last_price_change"],
            reverse=True,
        )[:8]
        biggest_discount = max((int(card["discount_percent"]) for card in cards), default=0)

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "products": cards,
                "total_products": total_products,
                "average_price": average_price,
                "highest_price": highest_price,
                "lowest_price": lowest_price,
                "featured_categories": featured_categories,
                "main_categories": main_categories,
                "grouped_product_count": grouped_product_count,
                "best_deals": best_deals,
                "top_scored_products": top_scored_products,
                "price_drop_products": price_drop_products,
                "newest_products": newest_products,
                "biggest_discount": biggest_discount,
            },
        )
    finally:
        db.close()


@router.get("/api/search/suggestions")
def search_suggestions(q: str = ""):
    """Ana sayfadaki arama kutusu için hızlı ürün grubu önerileri."""
    cleaned = " ".join(str(q or "").split()).strip()
    if len(cleaned) < 2:
        return JSONResponse({"items": []})

    db = SessionLocal()
    try:
        pattern = f"%{cleaned}%"
        groups = (
            db.query(ProductGroup)
            .filter(
                or_(
                    ProductGroup.canonical_name.ilike(pattern),
                    ProductGroup.brand.ilike(pattern),
                    ProductGroup.model.ilike(pattern),
                    ProductGroup.category.ilike(pattern),
                )
            )
            .order_by(ProductGroup.updated_at.desc())
            .limit(8)
            .all()
        )
        items = []
        for group in groups:
            best_offer = (
                db.query(ProductOffer, Store)
                .join(Store, Store.id == ProductOffer.store_id)
                .filter(ProductOffer.group_id == group.id)
                .order_by(ProductOffer.current_price.asc())
                .first()
            )
            offer, store = best_offer if best_offer else (None, None)
            items.append(
                {
                    "name": group.canonical_name,
                    "brand": group.brand,
                    "category": group.category,
                    "image": group.image,
                    "price": float(offer.current_price) if offer else None,
                    "store": store.name if store else None,
                    "url": f"/karsilastir/{group.group_key}",
                }
            )
        return JSONResponse({"items": items})
    finally:
        db.close()


COLLECTION_PAGE_SIZE = 24


def _request_float(value: str | None) -> float | None:
    if value is None:
        return None

    normalized = value.strip().replace(".", "").replace(",", ".")

    if not normalized:
        return None

    try:
        return float(normalized)
    except ValueError:
        return None


def _request_int(value: str | None) -> int | None:
    if value is None:
        return None

    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return None


def _collection_sort_key(card: dict[str, object], sort: str):
    if sort == "price_asc":
        return (
            _safe_float(card.get("price"), float("inf")),
            str(card.get("name", "")).casefold(),
        )

    if sort == "price_desc":
        return (
            -_safe_float(card.get("price"), 0),
            str(card.get("name", "")).casefold(),
        )

    if sort == "discount":
        return (
            -int(card.get("discount_percent", 0) or 0),
            -int(card.get("ai_score", 0) or 0),
        )

    if sort == "score":
        return (
            -int(card.get("ai_score", 0) or 0),
            -int(card.get("discount_percent", 0) or 0),
        )

    if sort == "rating":
        return (
            -_safe_float(card.get("rating"), 0),
            -int(card.get("review_count", 0) or 0),
        )

    return (
        -int(card.get("discount_percent", 0) or 0),
        -int(card.get("ai_score", 0) or 0),
    )


def _build_collection_context(
    request: Request,
    products: list,
    *,
    page_title: str,
    page_description: str,
    page_kicker: str,
    active_nav: str,
    default_sort: str,
) -> dict[str, object]:
    params = request.query_params

    search_text = str(params.get("q", "") or "").strip()
    selected_category = str(
        params.get("category", "") or ""
    ).strip()
    selected_sort = str(
        params.get("sort", default_sort) or default_sort
    ).strip()

    allowed_sorts = {
        "recommended",
        "discount",
        "score",
        "price_asc",
        "price_desc",
        "rating",
    }

    if selected_sort not in allowed_sorts:
        selected_sort = default_sort

    minimum_price = _request_float(params.get("min_price"))
    maximum_price = _request_float(params.get("max_price"))
    minimum_score = _request_int(params.get("min_score"))
    requested_page = _request_int(params.get("page")) or 1
    current_page = max(1, requested_page)

    cards = [_product_card(product) for product in products]

    all_categories = sorted(
        {
            str(card.get("category", "") or "").strip()
            for card in cards
            if str(card.get("category", "") or "").strip()
        },
        key=str.casefold,
    )

    if search_text:
        normalized_search = search_text.casefold()

        cards = [
            card
            for card in cards
            if normalized_search
            in " ".join(
                (
                    str(card.get("name", "")),
                    str(card.get("seller", "")),
                    str(card.get("category", "")),
                )
            ).casefold()
        ]

    if selected_category:
        normalized_category = selected_category.casefold()

        cards = [
            card
            for card in cards
            if str(card.get("category", "")).casefold()
            == normalized_category
        ]

    if minimum_price is not None:
        cards = [
            card
            for card in cards
            if _safe_float(card.get("price"), 0) >= minimum_price
        ]

    if maximum_price is not None:
        cards = [
            card
            for card in cards
            if _safe_float(card.get("price"), 0) <= maximum_price
        ]

    if minimum_score is not None:
        cards = [
            card
            for card in cards
            if int(card.get("ai_score", 0) or 0) >= minimum_score
        ]

    cards.sort(
        key=lambda card: _collection_sort_key(
            card,
            selected_sort,
        )
    )

    total_results = len(cards)
    total_pages = max(
        1,
        (total_results + COLLECTION_PAGE_SIZE - 1)
        // COLLECTION_PAGE_SIZE,
    )
    current_page = min(current_page, total_pages)

    start_index = (current_page - 1) * COLLECTION_PAGE_SIZE
    end_index = start_index + COLLECTION_PAGE_SIZE
    paginated_cards = cards[start_index:end_index]

    preserved_params = {
        "q": search_text,
        "category": selected_category,
        "sort": selected_sort,
        "min_price": (
            params.get("min_price", "")
            if minimum_price is not None
            else ""
        ),
        "max_price": (
            params.get("max_price", "")
            if maximum_price is not None
            else ""
        ),
        "min_score": (
            str(minimum_score)
            if minimum_score is not None
            else ""
        ),
    }

    def page_url(page_number: int) -> str:
        query_values = {
            key: value
            for key, value in preserved_params.items()
            if value not in ("", None)
        }
        query_values["page"] = page_number
        return f"{request.url.path}?{urlencode(query_values)}"

    page_numbers = list(
        range(
            max(1, current_page - 2),
            min(total_pages, current_page + 2) + 1,
        )
    )

    return {
        "request": request,
        "page_title": page_title,
        "page_description": page_description,
        "page_kicker": page_kicker,
        "products": paginated_cards,
        "active_nav": active_nav,
        "categories": all_categories,
        "search_text": search_text,
        "selected_category": selected_category,
        "selected_sort": selected_sort,
        "minimum_price_value": params.get("min_price", ""),
        "maximum_price_value": params.get("max_price", ""),
        "minimum_score_value": (
            str(minimum_score)
            if minimum_score is not None
            else ""
        ),
        "total_results": total_results,
        "current_page": current_page,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "previous_page_url": (
            page_url(current_page - 1)
            if current_page > 1
            else None
        ),
        "next_page_url": (
            page_url(current_page + 1)
            if current_page < total_pages
            else None
        ),
        "page_url": page_url,
        "filters_active": any(
            (
                search_text,
                selected_category,
                minimum_price is not None,
                maximum_price is not None,
                minimum_score is not None,
            )
        ),
    }




@router.get("/firsatlar")
def deals_page(request: Request):
    db = SessionLocal()

    try:
        products = db.query(ProductDB).all()

        deal_products = [
            product
            for product in products
            if _calculate_discount_percent(product) > 0
        ]

        context = _build_collection_context(
            request,
            deal_products,
            page_title="Günün En İyi Fırsatları",
            page_description=(
                "İndirim oranı ve Fırsat Skoru birlikte "
                "değerlendirilerek sıralanan ürünler."
            ),
            page_kicker="Fırsatlar",
            active_nav="deals",
            default_sort="discount",
        )

        return templates.TemplateResponse(
            request=request,
            name="product_collection_v3.html",
            context=context,
        )
    finally:
        db.close()


@router.get("/fiyati-dusenler")
def price_drops_page(request: Request):
    db = SessionLocal()

    try:
        products = db.query(ProductDB).all()

        dropped_products = [
            product
            for product in products
            if _calculate_discount_percent(product) > 0
        ]

        context = _build_collection_context(
            request,
            dropped_products,
            page_title="Fiyatı Düşen Ürünler",
            page_description=(
                "Eski fiyatına göre düşüş gösteren güncel "
                "ürünleri tek sayfada incele."
            ),
            page_kicker="Fiyat alarmı",
            active_nav="price-drops",
            default_sort="discount",
        )

        return templates.TemplateResponse(
            request=request,
            name="product_collection_v3.html",
            context=context,
        )
    finally:
        db.close()


@router.get("/ai-tavsiyeleri")
def ai_recommendations_page(request: Request):
    db = SessionLocal()

    try:
        products = db.query(ProductDB).all()

        scored_products = [
            product
            for product in products
            if int(getattr(product, "ai_score", 0) or 0) > 0
        ]

        context = _build_collection_context(
            request,
            scored_products,
            page_title="AI Tavsiyeleri",
            page_description=(
                "Fiyat, indirim ve ürün verileri birlikte "
                "değerlendirilerek öne çıkarılan ürünler."
            ),
            page_kicker="Yapay zekâ seçimi",
            active_nav="ai",
            default_sort="score",
        )

        return templates.TemplateResponse(
            request=request,
            name="product_collection_v3.html",
            context=context,
        )
    finally:
        db.close()


@router.get("/kategoriler")
def categories_page(request: Request):
    db = SessionLocal()

    try:
        database_category_rows = (
            db.query(
                ProductGroup.category,
                func.count(ProductGroup.id),
            )
            .filter(
                ProductGroup.category.isnot(None),
                ProductGroup.category != "",
            )
            .group_by(ProductGroup.category)
            .all()
        )

        category_catalog = build_category_catalog(
            database_category_rows
        )
        featured_categories = build_featured_categories(
            category_catalog
        )

        total_catalog_items = sum(
            len(group["items"])
            for main_category in category_catalog
            for group in main_category["groups"]
        )

        return templates.TemplateResponse(
            request=request,
            name="categories.html",
            context={
                "category_catalog": category_catalog,
                "featured_categories": featured_categories,
                "total_catalog_items": total_catalog_items,
            },
        )
    finally:
        db.close()


@router.get("/history/{product_id}")
def history(product_id: int):
    db = SessionLocal()

    try:
        history_items = (
            db.query(PriceHistory)
            .filter(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.created_at)
            .all()
        )

        return JSONResponse(
            [
                {
                    "price": item.price,
                    "date": item.created_at.strftime(
                        "%d.%m.%Y %H:%M",
                    ),
                }
                for item in history_items
            ]
        )

    finally:
        db.close()


@router.get("/products")
def products():
    db = SessionLocal()

    try:
        items = db.query(ProductDB).all()

        return [
            {
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "old_price": item.old_price,
                "rating": item.rating,
                "review_count": item.review_count,
                "seller": item.seller,
                "url": item.url,
                "image": item.image,
                "ai_score": item.ai_score,
                "last_notified_price": item.last_notified_price,
            }
            for item in items
        ]

    finally:
        db.close()

# ---------------------------------------------------------------------------
# Aşama 5.3 - Gelişmiş ürün grubu araması ve dinamik filtreler
# ---------------------------------------------------------------------------
from collections import Counter
from math import ceil

from app.database.models import ProductOffer, ProductGroup, Store
from app.services.catalog_search_service import (
    calculate_relevance,
    parse_capacity_gb,
    parse_identity_attributes,
)


def _currency_filter(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    formatted = f"{number:,.0f}".replace(",", ".")
    return f"{formatted} ₺"


templates.env.filters["try_format_currency"] = _currency_filter


def _facet_rows(counter: Counter, *, capacity: bool = False):
    rows = []
    for value, count in counter.items():
        if not value:
            continue
        label = value
        if capacity:
            numeric = parse_capacity_gb(value)
            if numeric is not None:
                label = f"{numeric // 1024} TB" if numeric >= 1024 and numeric % 1024 == 0 else f"{numeric} GB"
        rows.append({"value": value, "label": label, "count": count})
    if capacity:
        rows.sort(key=lambda item: parse_capacity_gb(item["value"]) or 0)
    else:
        rows.sort(key=lambda item: (-item["count"], item["value"].casefold()))
    return rows


def _page_items(current_page: int, total_pages: int):
    values = {1, total_pages}
    values.update(range(max(1, current_page - 2), min(total_pages, current_page + 2) + 1))
    result = []
    previous = None
    for value in sorted(values):
        if previous is not None and value - previous > 1:
            result.append("…")
        result.append(value)
        previous = value
    return result


@router.get("/arama")
def advanced_catalog_search(request: Request):
    params = request.query_params
    query = " ".join(str(params.get("q", "") or "").split())
    selected_brands = [item.strip() for item in params.getlist("brand") if item.strip()]
    selected_categories = [item.strip() for item in params.getlist("category") if item.strip()]
    selected_storage = [item.strip() for item in params.getlist("storage") if item.strip()]
    selected_ram = [item.strip() for item in params.getlist("ram") if item.strip()]
    selected_sort = str(params.get("sort", "relevance") or "relevance")
    if selected_sort not in {"relevance", "price_asc", "price_desc", "stores", "newest"}:
        selected_sort = "relevance"

    min_price = _request_float(params.get("min_price"))
    max_price = _request_float(params.get("max_price"))
    current_page = max(1, _request_int(params.get("page")) or 1)
    page_size = 24

    db = SessionLocal()
    try:
        groups = db.query(ProductGroup).order_by(ProductGroup.updated_at.desc()).all()
        candidates = []
        for group in groups:
            rows = (
                db.query(ProductOffer, Store)
                .join(Store, Store.id == ProductOffer.store_id)
                .filter(ProductOffer.group_id == group.id)
                .order_by(ProductOffer.current_price.asc())
                .all()
            )
            valid_rows = [(offer, store) for offer, store in rows if float(offer.current_price or 0) > 0]
            if not valid_rows:
                continue
            best_offer, best_store = valid_rows[0]
            price = float(best_offer.current_price or 0)
            attrs = parse_identity_attributes(group.identity_source)
            score = calculate_relevance(
                query,
                name=group.canonical_name,
                brand=group.brand,
                model=group.model,
                category=group.category,
                identity_source=group.identity_source,
            )
            if query and score <= 0:
                continue
            candidates.append({
                "id": group.id,
                "name": group.canonical_name,
                "brand": str(group.brand or "").strip(),
                "model": str(group.model or "").strip(),
                "category": str(group.category or "").strip(),
                "image": group.image,
                "price": price,
                "offer_count": len(valid_rows),
                "best_store": best_store.name,
                "url": f"/karsilastir/{group.group_key}",
                "updated_at": group.updated_at,
                "relevance": score,
                "storage": attrs.get("storage", ""),
                "ram": attrs.get("ram", ""),
            })

        # Facet counts are generated before their own filters so users can widen choices.
        brand_facets = _facet_rows(Counter(item["brand"] for item in candidates if item["brand"]))
        category_facets = _facet_rows(Counter(item["category"] for item in candidates if item["category"]))
        storage_facets = _facet_rows(Counter(item["storage"] for item in candidates if item["storage"]), capacity=True)
        ram_facets = _facet_rows(Counter(item["ram"] for item in candidates if item["ram"]), capacity=True)

        if selected_brands:
            selected_set = {value.casefold() for value in selected_brands}
            candidates = [item for item in candidates if item["brand"].casefold() in selected_set]
        if selected_categories:
            selected_set = {value.casefold() for value in selected_categories}
            candidates = [item for item in candidates if item["category"].casefold() in selected_set]
        if selected_storage:
            selected_set = {value.casefold() for value in selected_storage}
            candidates = [item for item in candidates if item["storage"].casefold() in selected_set]
        if selected_ram:
            selected_set = {value.casefold() for value in selected_ram}
            candidates = [item for item in candidates if item["ram"].casefold() in selected_set]
        if min_price is not None:
            candidates = [item for item in candidates if item["price"] >= min_price]
        if max_price is not None:
            candidates = [item for item in candidates if item["price"] <= max_price]

        if selected_sort == "price_asc":
            candidates.sort(key=lambda item: (item["price"], item["name"].casefold()))
        elif selected_sort == "price_desc":
            candidates.sort(key=lambda item: (-item["price"], item["name"].casefold()))
        elif selected_sort == "stores":
            candidates.sort(key=lambda item: (-item["offer_count"], -item["relevance"], item["name"].casefold()))
        elif selected_sort == "newest":
            candidates.sort(key=lambda item: item["updated_at"], reverse=True)
        else:
            candidates.sort(key=lambda item: (-item["relevance"], -item["offer_count"], item["price"]))

        total_results = len(candidates)
        total_pages = max(1, ceil(total_results / page_size))
        current_page = min(current_page, total_pages)
        start = (current_page - 1) * page_size
        products = candidates[start:start + page_size]

        preserved_params = {
            "q": [query] if query else [],
            "brand": selected_brands,
            "category": selected_categories,
            "storage": selected_storage,
            "ram": selected_ram,
            "min_price": [str(params.get("min_price"))] if params.get("min_price") else [],
            "max_price": [str(params.get("max_price"))] if params.get("max_price") else [],
            "sort": [selected_sort],
        }

        def page_url(page_number: int):
            pairs = []
            for key, values in preserved_params.items():
                for value in values:
                    pairs.append((key, value))
            pairs.append(("page", str(page_number)))
            return f"/arama?{urlencode(pairs)}"

        numeric_pages = [value for value in _page_items(current_page, total_pages) if isinstance(value, int)]
        return templates.TemplateResponse(
            request=request,
            name="search_results.html",
            context={
                "page_title": f"{query} arama sonuçları" if query else "Tüm ürünler",
                "query": query,
                "products": products,
                "total_results": total_results,
                "selected_sort": selected_sort,
                "selected_brands": selected_brands,
                "selected_categories": selected_categories,
                "selected_storage": selected_storage,
                "selected_ram": selected_ram,
                "min_price_value": params.get("min_price", ""),
                "max_price_value": params.get("max_price", ""),
                "brand_facets": brand_facets,
                "category_facets": category_facets,
                "storage_facets": storage_facets,
                "ram_facets": ram_facets,
                "current_page": current_page,
                "total_pages": total_pages,
                "page_items": _page_items(current_page, total_pages),
                "page_urls": {page: page_url(page) for page in numeric_pages},
                "previous_url": page_url(current_page - 1) if current_page > 1 else None,
                "next_url": page_url(current_page + 1) if current_page < total_pages else None,
                "preserved_params": preserved_params,
            },
        )
    finally:
        db.close()
