from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from app.services.seo_url_service import product_url

ENGINE_VERSION = "13.6.4"


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).replace("ı", "i")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


@dataclass(frozen=True)
class LandingDefinition:
    slug: str
    title: str
    heading: str
    description: str
    category_terms: tuple[str, ...] = ()
    include_terms: tuple[str, ...] = ()
    price_min: float | None = None
    price_max: float | None = None
    sort: str = "price_asc"
    intro: str = ""

    @property
    def url(self) -> str:
        return f"/kesfet/{self.slug}"


LANDINGS: tuple[LandingDefinition, ...] = (
    LandingDefinition(
        slug="oyuncu-laptoplari",
        title="Oyuncu Laptopları ve Güncel Fiyatları | FırsatAI",
        heading="Oyuncu Laptopları",
        description="RTX, GTX ve oyuncu sınıfı laptop modellerinin mağaza fiyatlarını karşılaştırın.",
        category_terms=("laptop", "notebook", "dizustu"),
        include_terms=("rtx", "gtx", "gaming", "oyuncu", "victus", "tuf", "loq", "nitro", "legion"),
        sort="stores",
        intro="Oyun performansına odaklanan laptopları tek sayfada karşılaştırın; fiyat ve mağaza sayısına göre en uygun seçenekleri inceleyin.",
    ),
    LandingDefinition(
        slug="30000-tl-alti-telefonlar",
        title="30.000 TL Altı Telefonlar | FırsatAI",
        heading="30.000 TL Altı Telefonlar",
        description="30.000 TL altındaki telefon modellerini ve güncel mağaza fiyatlarını karşılaştırın.",
        category_terms=("telefon", "phone", "iphone", "android"),
        price_max=30000,
        sort="price_desc",
        intro="Belirlenen bütçe sınırını aşmayan telefonları fiyat, marka ve mağaza kapsamıyla birlikte görün.",
    ),
    LandingDefinition(
        slug="oled-monitorler",
        title="OLED Monitörler ve Fiyatları | FırsatAI",
        heading="OLED Monitörler",
        description="OLED panel monitör modellerini, fiyatlarını ve mağaza tekliflerini karşılaştırın.",
        category_terms=("monitor", "monitor"),
        include_terms=("oled",),
        sort="price_asc",
        intro="OLED panel kullanan monitörleri güncel fiyatları ve mağaza teklifleriyle karşılaştırın.",
    ),
    LandingDefinition(
        slug="fiyati-dusen-laptoplar",
        title="Fiyatı Düşen Laptoplar | FırsatAI",
        heading="Fiyatı Düşen Laptoplar",
        description="Eski fiyatına göre indirime giren laptop modellerini karşılaştırın.",
        category_terms=("laptop", "notebook", "dizustu"),
        sort="price_drop",
        intro="Eski fiyatı bulunan ve güncel fiyatı düşen laptopları indirim oranına göre inceleyin.",
    ),
)


def list_landings() -> list[dict]:
    return [
        {
            "slug": item.slug,
            "title": item.title,
            "heading": item.heading,
            "description": item.description,
            "url": item.url,
            "price_min": item.price_min,
            "price_max": item.price_max,
        }
        for item in LANDINGS
    ]


def resolve_landing(slug: str) -> LandingDefinition | None:
    wanted = str(slug or "").strip().casefold()
    return next((item for item in LANDINGS if item.slug == wanted), None)


def _money(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _matches_category(category: object, terms: Iterable[str]) -> bool:
    if not terms:
        return True
    current = normalize_text(category)
    return any(normalize_text(term) in current or current in normalize_text(term) for term in terms if current)


def _matches_terms(group: object, terms: Iterable[str]) -> bool:
    wanted = tuple(normalize_text(term) for term in terms if str(term).strip())
    if not wanted:
        return True
    haystack = normalize_text(" ".join((str(group.canonical_name or ""), str(group.brand or ""), str(group.model or ""))))
    return any(term in haystack for term in wanted)


def landing_detail(db, landing: LandingDefinition, *, limit: int = 72) -> dict:
    from sqlalchemy import func
    from app.database.models import ProductGroup, ProductOffer

    rows = (
        db.query(
            ProductGroup,
            func.min(ProductOffer.current_price).label("min_price"),
            func.max(ProductOffer.old_price).label("old_price"),
            func.count(ProductOffer.id).label("offer_count"),
            func.count(func.distinct(ProductOffer.store_id)).label("store_count"),
        )
        .join(ProductOffer, ProductOffer.group_id == ProductGroup.id)
        .filter(ProductOffer.current_price > 0)
        .group_by(ProductGroup.id)
        .all()
    )

    cards: list[dict] = []
    brands: dict[str, int] = {}
    categories: dict[str, int] = {}
    for group, min_price, old_price, offer_count, store_count in rows:
        price = _money(min_price)
        if not _matches_category(group.category, landing.category_terms):
            continue
        if not _matches_terms(group, landing.include_terms):
            continue
        if landing.price_min is not None and price < landing.price_min:
            continue
        if landing.price_max is not None and price > landing.price_max:
            continue
        previous = _money(old_price)
        drop = round(max(0.0, (previous - price) / previous * 100), 2) if previous > price > 0 else 0.0
        if landing.sort == "price_drop" and drop <= 0:
            continue
        brand = str(group.brand or "Markasız").strip() or "Markasız"
        category = str(group.category or "Diğer").strip() or "Diğer"
        brands[brand] = brands.get(brand, 0) + 1
        categories[category] = categories.get(category, 0) + 1
        cards.append(
            {
                "id": group.id,
                "identity_key": group.group_key,
                "name": group.canonical_name,
                "brand": brand,
                "category": category,
                "image": group.image,
                "price": price,
                "old_price": previous,
                "price_drop_percent": drop,
                "offer_count": int(offer_count or 0),
                "store_count": int(store_count or 0),
                "detail_url": product_url(group.canonical_name, group.group_key),
                "updated_at": group.updated_at,
            }
        )

    if landing.sort == "price_desc":
        cards.sort(key=lambda item: (-item["price"], item["name"]))
    elif landing.sort == "stores":
        cards.sort(key=lambda item: (-item["store_count"], item["price"], item["name"]))
    elif landing.sort == "price_drop":
        cards.sort(key=lambda item: (-item["price_drop_percent"], item["price"], item["name"]))
    else:
        cards.sort(key=lambda item: (item["price"] <= 0, item["price"], item["name"]))

    cards = cards[: max(1, min(int(limit or 72), 200))]
    prices = [item["price"] for item in cards if item["price"] > 0]
    return {
        "engine_version": ENGINE_VERSION,
        "read_only": True,
        "landing": {
            "slug": landing.slug,
            "title": landing.title,
            "heading": landing.heading,
            "description": landing.description,
            "intro": landing.intro,
            "url": landing.url,
            "price_min": landing.price_min,
            "price_max": landing.price_max,
            "sort": landing.sort,
        },
        "cards": cards,
        "product_count": len(cards),
        "lowest_price": min(prices) if prices else 0.0,
        "highest_price": max(prices) if prices else 0.0,
        "brand_count": len(brands),
        "category_count": len(categories),
        "brands": sorted(brands.items(), key=lambda item: (-item[1], item[0]))[:12],
        "categories": sorted(categories.items(), key=lambda item: (-item[1], item[0]))[:12],
        "related": [item for item in list_landings() if item["slug"] != landing.slug][:3],
    }
