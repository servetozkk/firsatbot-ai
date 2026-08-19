from pathlib import Path
from difflib import SequenceMatcher
import re
import unicodedata

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
from app.web.account_routes import _current_user
from app.services.smart_search_service import enrich_and_rank_candidates, parse_smart_query
from app.services.advanced_filter_service import build_dynamic_facets, apply_dynamic_filters, filter_metadata
from app.services.advanced_sort_service import SORT_OPTIONS, sort_candidates

from app.database.models import (
    PriceHistory,
    ProductDB,
    ProductGroup,
    ProductOffer,
    Store,
    Favorite,
    PriceAlert,
    RecentlyViewed,
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
        # Ana sayfa verisini N+1 sorgu oluşturmadan toplu olarak yükle.
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

        offer_rows = (
            db.query(ProductOffer, Store)
            .join(Store, Store.id == ProductOffer.store_id)
            .filter(ProductOffer.is_hidden.is_(False))
            .order_by(ProductOffer.group_id.asc(), ProductOffer.current_price.asc())
            .all()
        )
        offers_by_group: dict[int, list[tuple[ProductOffer, Store]]] = {}
        for offer, store in offer_rows:
            offers_by_group.setdefault(int(offer.group_id), []).append((offer, store))

        cards: list[dict[str, object]] = []
        unavailable_values = {"stokta yok", "out of stock", "unavailable"}
        for group in groups:
            offers = offers_by_group.get(int(group.id), [])
            if not offers:
                continue

            available_rows = [
                (offer, store)
                for offer, store in offers
                if str(offer.availability or "").casefold() not in unavailable_values
            ] or offers

            priced_rows = [
                (offer, store)
                for offer, store in available_rows
                if float(offer.current_price or 0) > 0
            ]
            if not priced_rows:
                continue

            best_offer, best_store = min(
                priced_rows,
                key=lambda row: float(row[0].current_price or float("inf")),
            )
            prices = [float(offer.current_price or 0) for offer, _ in priced_rows]
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
                    "group_key": group.group_key,
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
                    "brand": group.brand or "",
                    "stock_status": best_offer.availability or "Bilinmiyor",
                    "detail_url": f"/urun/{group.group_key}",
                    "store_url": best_offer.url,
                    "created_at": group.created_at,
                    "last_price_change": best_offer.updated_at,
                    "offer_count": len(priced_rows),
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
        total_offer_count = sum(int(card.get("offer_count") or 0) for card in cards)
        most_compared_products = sorted(
            cards,
            key=lambda card: (int(card.get("offer_count") or 0), int(card.get("review_count") or 0)),
            reverse=True,
        )[:8]

        popular_store_rows = (
            db.query(Store.name, func.count(ProductOffer.id))
            .join(ProductOffer, ProductOffer.store_id == Store.id)
            .filter(Store.name.isnot(None), Store.name != "")
            .group_by(Store.id, Store.name)
            .order_by(func.count(ProductOffer.id).desc(), Store.name.asc())
            .limit(8)
            .all()
        )
        store_logo_map = {
            "trendyol": "/static/img/stores/trendyol.svg",
            "hepsiburada": "/static/img/stores/hepsiburada.svg",
            "amazon": "/static/img/stores/amazon.svg",
            "teknosa": "/static/img/stores/teknosa.svg",
            "mediamarkt": "/static/img/stores/mediamarkt.svg",
            "media markt": "/static/img/stores/mediamarkt.svg",
            "n11": "/static/img/stores/n11.svg",
            "çiçeksepeti": "/static/img/stores/ciceksepeti.svg",
            "cicek sepeti": "/static/img/stores/ciceksepeti.svg",
        }

        popular_stores = []
        for name, offer_count in popular_store_rows:
            store_name = str(name).strip()
            normalized_store_name = store_name.casefold()
            logo_url = store_logo_map.get(normalized_store_name)
            if logo_url is None:
                for keyword, mapped_logo in store_logo_map.items():
                    if keyword in normalized_store_name:
                        logo_url = mapped_logo
                        break

            popular_stores.append(
                {
                    "name": store_name,
                    "offer_count": int(offer_count or 0),
                    "initial": store_name[:1].upper() or "M",
                    "logo_url": logo_url or "/static/img/stores/generic.svg",
                    "search_url": f"/magaza/{urlencode({'x': store_name})[2:]}",
                }
            )

        brand_counts: dict[str, int] = {}
        for card in cards:
            brand = str(card.get("brand") or "").strip()
            if brand:
                brand_counts[brand] = brand_counts.get(brand, 0) + 1

        popular_brands = [
            {
                "name": brand,
                "product_count": count,
                "initial": brand[:1].upper(),
                "url": f"/marka/{urlencode({'x': brand})[2:]}",
            }
            for brand, count in sorted(
                brand_counts.items(),
                key=lambda item: (-item[1], item[0].lower()),
            )[:10]
        ]

        featured_deal = best_deals[0] if best_deals else (top_scored_products[0] if top_scored_products else None)
        price_drop_count = len([card for card in cards if float(card["old_price"] or 0) > float(card["price"] or 0)])
        multi_store_count = len([card for card in cards if int(card.get("offer_count") or 0) > 1])
        total_saving_potential = round(
            sum(float(card.get("saving_amount") or 0) for card in best_deals),
            2,
        )

        current_user = _current_user(db, request.cookies.get("firsat_session"))

        personalized_home = False
        user_favorite_count = 0
        user_active_alert_count = 0
        user_recent_count = 0
        favorite_deals: list[dict[str, object]] = []
        recently_viewed_products: list[dict[str, object]] = []
        recommended_for_user: list[dict[str, object]] = []
        user_interest_categories: list[str] = []

        if current_user is not None:
            personalized_home = True
            visitor_key = f"user:{current_user.id}"
            card_by_group_id = {int(card["id"]): card for card in cards}

            favorite_rows = (
                db.query(Favorite)
                .filter(Favorite.visitor_id == visitor_key)
                .order_by(Favorite.created_at.desc())
                .all()
            )
            active_alert_rows = (
                db.query(PriceAlert)
                .filter(
                    PriceAlert.visitor_id == visitor_key,
                    PriceAlert.is_active.is_(True),
                )
                .all()
            )
            recent_rows = (
                db.query(RecentlyViewed)
                .filter(RecentlyViewed.user_id == current_user.id)
                .order_by(RecentlyViewed.viewed_at.desc())
                .limit(20)
                .all()
            )

            user_favorite_count = len(favorite_rows)
            user_active_alert_count = len(active_alert_rows)
            user_recent_count = len(recent_rows)

            favorite_ids = [row.product_group_id for row in favorite_rows]
            recent_ids = [row.product_group_id for row in recent_rows]
            favorite_deals = [
                card_by_group_id[group_id]
                for group_id in favorite_ids
                if group_id in card_by_group_id
                and int(card_by_group_id[group_id].get("discount_percent") or 0) > 0
            ][:8]
            recently_viewed_products = [
                card_by_group_id[group_id]
                for group_id in recent_ids
                if group_id in card_by_group_id
            ][:8]

            category_weights: dict[str, int] = {}
            for group_id in favorite_ids:
                card = card_by_group_id.get(group_id)
                if card and card.get("category"):
                    category = str(card["category"])
                    category_weights[category] = category_weights.get(category, 0) + 3
            for group_id in recent_ids:
                card = card_by_group_id.get(group_id)
                if card and card.get("category"):
                    category = str(card["category"])
                    category_weights[category] = category_weights.get(category, 0) + 1

            user_interest_categories = [
                item[0]
                for item in sorted(category_weights.items(), key=lambda item: (-item[1], item[0]))[:3]
            ]
            excluded_ids = set(favorite_ids) | set(recent_ids[:4])
            recommendation_pool = [
                card for card in cards
                if int(card["id"]) not in excluded_ids
                and (not user_interest_categories or str(card.get("category") or "") in user_interest_categories)
            ]
            recommendation_pool.sort(
                key=lambda card: (
                    int(card.get("ai_score") or 0),
                    int(card.get("discount_percent") or 0),
                    int(card.get("offer_count") or 0),
                ),
                reverse=True,
            )
            recommended_for_user = recommendation_pool[:8]
            if not recommended_for_user:
                recommended_for_user = top_scored_products[:8]

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "current_user": current_user,
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
                "total_offer_count": total_offer_count,
                "most_compared_products": most_compared_products,
                "popular_stores": popular_stores,
                "popular_brands": popular_brands,
                "featured_deal": featured_deal,
                "price_drop_count": price_drop_count,
                "multi_store_count": multi_store_count,
                "total_saving_potential": total_saving_potential,
                "personalized_home": personalized_home,
                "user_favorite_count": user_favorite_count,
                "user_active_alert_count": user_active_alert_count,
                "user_recent_count": user_recent_count,
                "favorite_deals": favorite_deals,
                "recently_viewed_products": recently_viewed_products,
                "recommended_for_user": recommended_for_user,
                "user_interest_categories": user_interest_categories,
            },
        )
    finally:
        db.close()


@router.get("/api/search/suggestions")
def search_suggestions(q: str = ""):
    """Ürün, marka, kategori ve mağazaları tek akıllı arama panelinde döndürür."""
    cleaned = " ".join(str(q or "").split()).strip()
    if len(cleaned) < 2:
        return JSONResponse({"query": cleaned, "corrected_query": None, "sections": [], "items": []})

    def normalize(value: str | None) -> str:
        raw = unicodedata.normalize("NFKD", str(value or "").casefold())
        raw = "".join(char for char in raw if not unicodedata.combining(char))
        return re.sub(r"[^a-z0-9]+", " ", raw).strip()

    normalized_query = normalize(cleaned)
    db = SessionLocal()
    try:
        pattern = f"%{cleaned}%"
        direct_groups = (
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
            .limit(12)
            .all()
        )

        candidate_groups = direct_groups
        corrected_query = None
        if len(candidate_groups) < 5:
            pool = db.query(ProductGroup).order_by(ProductGroup.updated_at.desc()).limit(400).all()
            scored = []
            for group in pool:
                haystacks = [group.canonical_name, group.brand, group.model, group.category]
                score = max(
                    SequenceMatcher(None, normalized_query, normalize(value)).ratio()
                    for value in haystacks if value
                ) if any(haystacks) else 0
                name_norm = normalize(group.canonical_name)
                token_bonus = sum(0.08 for token in normalized_query.split() if token and token in name_norm)
                scored.append((score + token_bonus, group))
            scored.sort(key=lambda item: item[0], reverse=True)
            seen_ids = {group.id for group in candidate_groups}
            for score, group in scored:
                if score < 0.48 or group.id in seen_ids:
                    continue
                candidate_groups.append(group)
                seen_ids.add(group.id)
                if len(candidate_groups) >= 10:
                    break
            if not direct_groups and scored and scored[0][0] >= 0.62:
                corrected_query = scored[0][1].canonical_name

        product_items = []
        for group in candidate_groups[:8]:
            best_offer = (
                db.query(ProductOffer, Store)
                .join(Store, Store.id == ProductOffer.store_id)
                .filter(ProductOffer.group_id == group.id)
                .order_by(ProductOffer.current_price.asc())
                .first()
            )
            offer, store = best_offer if best_offer else (None, None)
            product_items.append({
                "type": "product",
                "name": group.canonical_name,
                "brand": group.brand,
                "category": group.category,
                "image": group.image,
                "price": float(offer.current_price) if offer else None,
                "store": store.name if store else None,
                "url": f"/karsilastir/{group.group_key}",
            })

        brands = [row[0] for row in (
            db.query(ProductGroup.brand)
            .filter(ProductGroup.brand.isnot(None), ProductGroup.brand != "")
            .distinct().limit(250).all()
        )]
        categories = [row[0] for row in (
            db.query(ProductGroup.category)
            .filter(ProductGroup.category.isnot(None), ProductGroup.category != "")
            .distinct().limit(250).all()
        )]
        stores = [row[0] for row in db.query(Store.name).filter(Store.name.isnot(None), Store.name != "").distinct().limit(250).all()]

        def ranked_entities(values, kind, limit=4):
            ranked=[]
            for value in values:
                norm=normalize(value)
                ratio=SequenceMatcher(None, normalized_query, norm).ratio()
                if normalized_query in norm:
                    ratio += 0.45
                if norm.startswith(normalized_query):
                    ratio += 0.25
                if ratio >= 0.52:
                    ranked.append((ratio, value))
            ranked.sort(key=lambda item: (-item[0], normalize(item[1])))
            result=[]
            for _, value in ranked[:limit]:
                if kind == 'brand':
                    url=f"/marka/{value}"
                    icon='🏷️'
                elif kind == 'category':
                    url=f"/arama?category={value}"
                    icon='📂'
                else:
                    url=f"/magaza/{value}"
                    icon='🏪'
                result.append({"type": kind, "name": value, "url": url, "icon": icon})
            return result

        sections=[]
        entity_sections = [
            ("products", "Ürünler", product_items),
            ("brands", "Markalar", ranked_entities(brands, "brand")),
            ("categories", "Kategoriler", ranked_entities(categories, "category")),
            ("stores", "Mağazalar", ranked_entities(stores, "store")),
        ]
        for key, title, items in entity_sections:
            if items:
                sections.append({"key": key, "title": title, "items": items})

        return JSONResponse({
            "query": cleaned,
            "corrected_query": corrected_query,
            "sections": sections,
            "items": product_items,
            "total": sum(len(section["items"]) for section in sections),
        })
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
                "sort_options": SORT_OPTIONS,
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
from app.services.global_catalog_search_service import build_global_search_candidates


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


@router.get("/api/filters/v13")
def advanced_filter_metadata(request: Request):
    categories=[item.strip() for item in request.query_params.getlist("category") if item.strip()]
    return filter_metadata(categories)


@router.get("/arama")
def advanced_catalog_search(request: Request):
    params = request.query_params
    query = " ".join(str(params.get("q", "") or "").split())
    smart_query = parse_smart_query(query)
    selected_brands = [item.strip() for item in params.getlist("brand") if item.strip()]
    selected_categories = [item.strip() for item in params.getlist("category") if item.strip()]
    selected_storage = [item.strip() for item in params.getlist("storage") if item.strip()]
    selected_ram = [item.strip() for item in params.getlist("ram") if item.strip()]
    selected_stores = [item.strip() for item in params.getlist("store") if item.strip()]
    selected_dynamic = {
        key.removeprefix("attr_"): [item.strip() for item in params.getlist(key) if item.strip()]
        for key in params.keys()
        if key.startswith("attr_")
    }
    only_in_stock = str(params.get("in_stock", "") or "").lower() in {"1", "true", "on", "yes"}
    only_free_shipping = str(params.get("free_shipping", "") or "").lower() in {"1", "true", "on", "yes"}
    selected_sort = str(params.get("sort", "relevance") or "relevance")
    if selected_sort not in SORT_OPTIONS:
        selected_sort = "relevance"

    min_price = _request_float(params.get("min_price"))
    max_price = _request_float(params.get("max_price"))
    current_page = max(1, _request_int(params.get("page")) or 1)
    page_size = 24

    db = SessionLocal()
    try:
        candidates = build_global_search_candidates(
            db=db,
            query=smart_query.get("search_text") or query,
        )
        candidates = enrich_and_rank_candidates(candidates, smart_query)
        if min_price is None and smart_query.get("price_min") is not None:
            min_price = float(smart_query["price_min"])
        if max_price is None and smart_query.get("price_max") is not None:
            max_price = float(smart_query["price_max"])

        # Facet counts are generated before their own filters so users can widen choices.
        brand_facets = _facet_rows(Counter(item["brand"] for item in candidates if item["brand"]))
        category_facets = _facet_rows(Counter(item["category"] for item in candidates if item["category"]))
        storage_facets = _facet_rows(Counter(item["storage"] for item in candidates if item["storage"]), capacity=True)
        ram_facets = _facet_rows(Counter(item["ram"] for item in candidates if item["ram"]), capacity=True)
        store_facets = _facet_rows(Counter(store for item in candidates for store in item["stores"] if store))

        # v13.4.0: kategoriye duyarlı dinamik filtre şeması ve sayaçları
        dynamic_facets = build_dynamic_facets(candidates, selected_categories)

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
        if selected_stores:
            selected_set = {value.casefold() for value in selected_stores}
            store_filtered_candidates = []
            for item in candidates:
                matching_offers = [
                    offer for offer in item["offers"]
                    if offer["store"].casefold() in selected_set
                ]
                if not matching_offers:
                    continue
                matching_offers.sort(key=lambda offer: offer.get("total_price", offer["price"]))
                item = dict(item)
                item["price"] = matching_offers[0].get("total_price", matching_offers[0]["price"])
                item["best_store"] = matching_offers[0]["store"]
                item["offer_count"] = len(matching_offers)
                item["in_stock"] = any(
                    not any(word in offer["availability"].casefold() for word in ("yok", "tükendi", "stok dışı", "out of stock"))
                    for offer in matching_offers
                )
                item["free_shipping"] = any(
                    offer["shipping_price"] is not None and offer["shipping_price"] <= 0
                    for offer in matching_offers
                )
                store_filtered_candidates.append(item)
            candidates = store_filtered_candidates
        candidates = apply_dynamic_filters(candidates, selected_dynamic)
        if only_in_stock:
            candidates = [item for item in candidates if item["in_stock"]]
        if only_free_shipping:
            candidates = [item for item in candidates if item["free_shipping"]]
        if min_price is not None:
            candidates = [item for item in candidates if item["price"] >= min_price]
        if max_price is not None:
            candidates = [item for item in candidates if item["price"] <= max_price]

        # v13.4.1: Akakçe tarzı açıklanabilir sıralama motoru
        candidates = sort_candidates(candidates, selected_sort)

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
            "store": selected_stores,
            "in_stock": ["1"] if only_in_stock else [],
            "free_shipping": ["1"] if only_free_shipping else [],
            **{f"attr_{key}": values for key, values in selected_dynamic.items()},
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
                "smart_query": smart_query,
                "products": products,
                "total_results": total_results,
                "selected_sort": selected_sort,
                "sort_options": SORT_OPTIONS,
                "selected_brands": selected_brands,
                "selected_categories": selected_categories,
                "selected_storage": selected_storage,
                "selected_ram": selected_ram,
                "selected_stores": selected_stores,
                "selected_dynamic": selected_dynamic,
                "only_in_stock": only_in_stock,
                "only_free_shipping": only_free_shipping,
                "min_price_value": params.get("min_price", ""),
                "max_price_value": params.get("max_price", ""),
                "brand_facets": brand_facets,
                "category_facets": category_facets,
                "storage_facets": storage_facets,
                "ram_facets": ram_facets,
                "store_facets": store_facets,
                "dynamic_facets": dynamic_facets,
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
