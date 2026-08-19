from __future__ import annotations

from collections import OrderedDict
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Cookie,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_

from app.database.database import SessionLocal
from app.database.models import (
    ProductFeature,
    ProductDB,
    ProductFeatureValue,
    ProductGroup,
    ProductOffer,
    ProductImage,
    RecentlyViewed,
    GlobalProduct,
)
from app.services.seo_url_service import canonical_product_url, product_url
from app.services.schema_org_service import (
    breadcrumb_schema,
    dumps as schema_dumps,
    product_schema,
    website_schema,
)
from app.services.product_image_service import parse_image_gallery, dedupe_image_urls
from app.services.ai_comparison_service import (
    build_ai_comparison_analysis,
)
from app.services.comparison_service import (
    get_product_comparison,
)
from app.services.comparison_v2_service import (
    ENGINE_VERSION as COMPARISON_V2_VERSION,
    build_comparison_matrix,
    build_product_metrics,
    normalize_selected_keys,
)
from app.services.global_comparison_service import get_global_product_comparison
from app.services.global_price_history_service import get_global_price_history
from app.services.history_service import (
    get_product_price_history,
)
from app.services.price_analysis_service import build_price_analysis
from app.services.price_comparison_core_v21_service import get_product_price_comparison
from app.services.deal_intelligence_v13_service import build_deal_intelligence_v13
from app.services.ai_purchase_assistant_service import build_ai_purchase_assistant
from app.services.product_alternative_service import get_product_alternatives
from app.services.smart_recommendation_service import get_smart_recommendations
from app.services.community_service import get_product_community
from app.web.account_routes import _current_user

router = APIRouter(
    prefix="/karsilastir",
    tags=["Müşteri Ürün Karşılaştırma"],
)


BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates"),
)


def _extract_image_urls(value: Any) -> list[str]:
    """Tek bir URL, JSON dizi veya ayraçlı metinden görsel URL'leri çıkarır."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        result: list[str] = []
        for item in value:
            result.extend(_extract_image_urls(item))
        return result

    text = str(value).strip()
    if not text:
        return []

    if text.startswith("[") or text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                parsed = parsed.get("images") or parsed.get("urls") or parsed.get("gallery") or []
            return _extract_image_urls(parsed)
        except (json.JSONDecodeError, TypeError):
            pass

    # Bazı scraper çıktıları virgül, satır veya | ile birden fazla URL saklayabilir.
    candidates = re.split(r"[\n\r|;]+|,(?=\s*https?://)", text)
    return [item.strip().strip('"\'') for item in candidates if item.strip()]


def build_product_gallery(db: Any, group: ProductGroup, limit: int = 60) -> list[str]:
    """Ürün grubu ve bütün mağaza kayıtlarından mümkün olan tüm farklı görselleri oluşturur."""
    candidates: list[str] = []
    if group.image:
        candidates.append(group.image)

    product_ids = [row[0] for row in db.query(ProductOffer.product_id).filter(ProductOffer.group_id == group.id).all()]
    if product_ids:
        persistent = (db.query(ProductImage.image_url)
                      .filter(ProductImage.product_id.in_(product_ids))
                      .order_by(ProductImage.is_primary.desc(), ProductImage.sort_order.asc())
                      .all())
        candidates.extend(row[0] for row in persistent if row[0])

    rows = (
        db.query(ProductDB.image, ProductDB.image_gallery)
        .join(ProductOffer, ProductOffer.product_id == ProductDB.id)
        .filter(ProductOffer.group_id == group.id)
        .order_by(ProductOffer.is_best_offer.desc(), ProductOffer.updated_at.desc())
        .all()
    )
    for image, image_gallery in rows:
        if image:
            candidates.append(image)
        candidates.extend(parse_image_gallery(image_gallery))

    # Eski kayıtlarda image alanına JSON veya ayraçlı liste yazılmış olabilir.
    expanded: list[str] = []
    for value in candidates:
        expanded.extend(_extract_image_urls(value))
    return dedupe_image_urls(expanded, limit=limit)



def format_offer_freshness(value: Any) -> str:
    """Teklif kontrol zamanını kısa ve anlaşılır biçimde gösterir."""
    if value is None:
        return "Güncellik bilgisi yok"

    try:
        checked_at = value
        if isinstance(value, str):
            checked_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        now = datetime.now(checked_at.tzinfo) if getattr(checked_at, "tzinfo", None) else datetime.now()
        seconds = max(0, int((now - checked_at).total_seconds()))
    except (TypeError, ValueError, AttributeError):
        return "Güncellik bilgisi yok"

    if seconds < 60:
        return "Az önce kontrol edildi"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} dakika önce kontrol edildi"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} saat önce kontrol edildi"
    days = hours // 24
    return f"{days} gün önce kontrol edildi"


def build_offer_status(offer: dict[str, Any]) -> dict[str, str]:
    """Mevcut teklif verisinden stok ve güven metinleri üretir."""
    availability = str(offer.get("availability") or "Bilinmiyor").strip()
    normalized = availability.casefold()
    if any(term in normalized for term in ("stokta", "mevcut", "available", "var")):
        stock_code = "in-stock"
        stock_label = "Stokta"
    elif any(term in normalized for term in ("tükendi", "yok", "out of stock")):
        stock_code = "out-of-stock"
        stock_label = "Stokta yok"
    else:
        stock_code = "unknown"
        stock_label = availability or "Stok bilgisi yok"

    rating = offer.get("rating")
    review_count = int(offer.get("review_count") or 0)
    if rating is not None:
        trust_label = f"{float(rating):.1f} mağaza puanı"
        if review_count:
            trust_label += f" · {review_count:,} değerlendirme".replace(",", ".")
    else:
        trust_label = "Mağaza puanı henüz yok"

    return {
        "stock_code": stock_code,
        "stock_label": stock_label,
        "trust_label": trust_label,
        "freshness": format_offer_freshness(offer.get("last_checked_at") or offer.get("updated_at")),
    }


def resolve_store_logo(store_code: Any, store_name: Any) -> str | None:
    """Bilinen mağazalar için yerel logo yolunu döndürür."""
    normalized = " ".join(
        str(store_code or store_name or "").strip().lower().split()
    )
    compact = normalized.replace(" ", "").replace("-", "").replace("_", "")

    aliases = {
        "trendyol": "trendyol.svg",
        "hepsiburada": "hepsiburada.svg",
        "hb": "hepsiburada.svg",
        "amazon": "amazon.svg",
        "amazontr": "amazon.svg",
        "teknosa": "teknosa.svg",
        "mediamarkt": "mediamarkt.svg",
        "n11": "n11.svg",
        "ciceksepeti": "ciceksepeti.svg",
        "çiçeksepeti": "ciceksepeti.svg",
        "pazarama": "pazarama.svg",
    }

    filename = aliases.get(compact)
    return f"/static/img/stores/{filename}" if filename else None

def format_chart_date(
    raw_date: Optional[str],
) -> str:
    """
    ISO tarih değerini grafik üzerinde okunabilir
    Türkçe tarih biçimine dönüştürür.
    """

    if not raw_date:
        return "Tarih bilinmiyor"

    try:
        date_part, time_part = raw_date.split(
            "T",
            1,
        )

        year, month, day = date_part.split("-")

        cleaned_time = time_part[:5]

        return (
            f"{day}.{month}.{year} "
            f"{cleaned_time}"
        )

    except (ValueError, AttributeError):
        return str(raw_date)


def build_chart_datasets(
    history_data: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Mağaza fiyat geçmişlerini Chart.js için ortak
    etiket ve veri setlerine dönüştürür.
    """

    all_dates: set[str] = set()

    for store in history_data.get(
        "stores",
        [],
    ):
        for history_item in store.get(
            "history",
            [],
        ):
            created_at = history_item.get(
                "created_at"
            )

            if created_at:
                all_dates.add(
                    str(created_at)
                )

    sorted_dates = sorted(all_dates)

    chart_labels = [
        format_chart_date(date_value)
        for date_value in sorted_dates
    ]

    datasets: list[dict[str, Any]] = []

    for store in history_data.get(
        "stores",
        [],
    ):
        price_by_date = {
            str(item.get("created_at")): item.get(
                "price"
            )
            for item in store.get(
                "history",
                [],
            )
            if item.get("created_at")
        }

        data = [
            price_by_date.get(date_value)
            for date_value in sorted_dates
        ]

        current_price = store.get(
            "current_price"
        )

        if not sorted_dates:
            chart_labels = [
                "Güncel fiyat"
            ]

            data = [
                current_price
            ]

        elif (
            current_price is not None
            and all(
                value is None
                for value in data
            )
        ):
            data[-1] = current_price

        datasets.append(
            {
                "label": store.get(
                    "store",
                    "Mağaza",
                ),
                "store_code": store.get(
                    "store_code"
                ),
                "seller": store.get(
                    "seller"
                ),
                "data": data,
                "timestamps": sorted_dates,
            }
        )

    return chart_labels, datasets


def build_deal_badge(
    comparison: dict[str, Any],
    history_data: dict[str, Any],
) -> dict[str, Any]:
    """Geçmiş fiyat ve mağaza farkına göre kullanıcı rozeti üretir."""

    def number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    current = number(comparison.get("best_price"))
    historical_low = number(history_data.get("lowest_price"))
    historical_average = number(history_data.get("average_price"))
    saving_percent = number(comparison.get("saving_percent"))
    record_count = int(history_data.get("price_record_count", 0) or 0)

    distance_to_low = 100.0
    average_difference = 0.0

    if current > 0 and historical_low > 0:
        distance_to_low = max(0.0, ((current - historical_low) / historical_low) * 100)

    if current > 0 and historical_average > 0:
        average_difference = ((current - historical_average) / historical_average) * 100

    if record_count >= 2 and distance_to_low <= 1.0 and average_difference <= 0:
        return {
            "code": "super",
            "label": "Süper Fırsat",
            "description": "Takip edilen en düşük fiyat seviyesinde.",
            "score": 95,
        }

    if (record_count >= 2 and distance_to_low <= 5.0) or saving_percent >= 8:
        return {
            "code": "good",
            "label": "İyi Fiyat",
            "description": "Geçmişe veya diğer mağazalara göre avantajlı.",
            "score": 80,
        }

    if record_count < 2:
        return {
            "code": "new",
            "label": "Yeni Takip",
            "description": "Fiyatı değerlendirmek için daha fazla kayıt gerekiyor.",
            "score": 55,
        }

    if average_difference > 8:
        return {
            "code": "high",
            "label": "Fiyat Yüksek",
            "description": "Geçmiş ortalamanın belirgin biçimde üzerinde.",
            "score": 35,
        }

    return {
        "code": "normal",
        "label": "Normal Fiyat",
        "description": "Fiyat geçmiş aralığına yakın.",
        "score": 60,
    }


def _format_feature_number(value: float) -> str:
    """Teknik özellik sayılarını gereksiz sıfırlar olmadan biçimlendirir."""
    if float(value).is_integer():
        return str(int(value))

    return (
        f"{value:.4f}"
        .rstrip("0")
        .rstrip(".")
        .replace(".", ",")
    )


def _format_feature_value(
    feature: ProductFeature,
    value: ProductFeatureValue,
) -> str | None:
    """Özellik değerini ekranda gösterilecek metne dönüştürür."""
    value_type = (feature.value_type or "text").strip().lower()

    if value_type == "boolean":
        if value.value_boolean is None:
            return None
        return "Var" if value.value_boolean else "Yok"

    if value_type == "number":
        if value.value_number is None:
            return None

        formatted_value = _format_feature_number(value.value_number)
        unit = (feature.unit or "").strip()
        return f"{formatted_value} {unit}".strip()

    text_value = (value.value_text or value.raw_value or "").strip()
    return text_value or None


def _clean_feature_name(
    feature_name: str,
    display_value: str,
) -> str:
    """
    Scraper kaynaklı yapışık teknik özellik adlarını temizler.

    Örnek:
    Kapasite1 TB + 1 TB -> Kapasite
    Panel TipiIPS + IPS -> Panel Tipi
    HDMIVar + Var -> HDMI
    """
    cleaned_name = (feature_name or "").strip()
    cleaned_value = (display_value or "").strip()

    if not cleaned_name:
        return "Özellik"

    if not cleaned_value:
        return cleaned_name

    if cleaned_name.casefold().endswith(cleaned_value.casefold()):
        candidate = cleaned_name[:-len(cleaned_value)].strip()
        if candidate:
            return candidate

    compact_name = "".join(cleaned_name.split()).casefold()
    compact_value = "".join(cleaned_value.split()).casefold()

    if compact_value and compact_name.endswith(compact_value):
        keep_character_count = len(compact_name) - len(compact_value)
        non_space_count = 0
        cut_index = 0

        for index, character in enumerate(cleaned_name):
            if not character.isspace():
                non_space_count += 1

            if non_space_count >= keep_character_count:
                cut_index = index + 1
                break

        candidate = cleaned_name[:cut_index].strip()
        if candidate:
            return candidate

    return cleaned_name


def get_grouped_product_features(
    *,
    db: Any,
    product_group_id: int,
) -> list[dict[str, Any]]:
    """Ürün grubunun teknik özelliklerini bölüm bazında hazırlar."""
    rows = (
        db.query(ProductFeature, ProductFeatureValue)
        .join(
            ProductFeatureValue,
            ProductFeatureValue.feature_id == ProductFeature.id,
        )
        .filter(
            ProductFeatureValue.product_group_id == product_group_id,
            ProductFeature.is_active.is_(True),
        )
        .order_by(
            ProductFeature.section.asc(),
            ProductFeature.sort_order.asc(),
            ProductFeature.name.asc(),
        )
        .all()
    )

    grouped_features: OrderedDict[
        str,
        list[dict[str, Any]],
    ] = OrderedDict()

    for feature, value in rows:
        display_value = _format_feature_value(feature, value)

        if display_value is None:
            continue

        section_name = (
            (feature.section or "Genel").strip()
            or "Genel"
        )

        grouped_features.setdefault(section_name, []).append(
            {
                "id": feature.id,
                "code": feature.code,
                "name": _clean_feature_name(
                    feature.name,
                    display_value,
                ),
                "value": display_value,
                "value_type": feature.value_type,
                "comparison_type": feature.comparison_type,
            }
        )

    return [
        {
            "name": section_name,
            "features": features,
        }
        for section_name, features in grouped_features.items()
    ]



FEATURE_SECTION_META: dict[str, dict[str, Any]] = {
    "genel": {"label": "Genel", "icon": "📦", "order": 0},
    "temel bilgiler": {"label": "Temel Bilgiler", "icon": "📋", "order": 5},
    "ekran": {"label": "Ekran", "icon": "🖥️", "order": 10},
    "görüntü": {"label": "Görüntü", "icon": "🖥️", "order": 10},
    "işlemci": {"label": "İşlemci ve Performans", "icon": "⚙️", "order": 20},
    "performans": {"label": "İşlemci ve Performans", "icon": "⚙️", "order": 20},
    "bellek": {"label": "Bellek ve Depolama", "icon": "💾", "order": 30},
    "depolama": {"label": "Bellek ve Depolama", "icon": "💾", "order": 30},
    "kamera": {"label": "Kamera", "icon": "📷", "order": 40},
    "batarya": {"label": "Batarya ve Şarj", "icon": "🔋", "order": 50},
    "pil": {"label": "Batarya ve Şarj", "icon": "🔋", "order": 50},
    "bağlantı": {"label": "Bağlantılar", "icon": "📡", "order": 60},
    "kablosuz": {"label": "Bağlantılar", "icon": "📡", "order": 60},
    "ses": {"label": "Ses", "icon": "🎧", "order": 70},
    "tasarım": {"label": "Tasarım ve Fiziksel Özellikler", "icon": "📐", "order": 80},
    "fiziksel": {"label": "Tasarım ve Fiziksel Özellikler", "icon": "📐", "order": 80},
    "diğer": {"label": "Diğer Özellikler", "icon": "✨", "order": 90},
}

CATEGORY_HEADLINE_FEATURES: dict[str, tuple[str, ...]] = {
    "telefon": ("ekran", "işlemci", "ram", "depolama", "kamera", "batarya"),
    "smartphone": ("ekran", "işlemci", "ram", "depolama", "kamera", "batarya"),
    "laptop": ("işlemci", "ekran kartı", "ram", "ssd", "ekran", "yenileme"),
    "notebook": ("işlemci", "ekran kartı", "ram", "ssd", "ekran", "yenileme"),
    "monitor": ("ekran boyutu", "çözünürlük", "panel", "yenileme", "tepki", "hdr"),
    "televizyon": ("ekran boyutu", "çözünürlük", "panel", "yenileme", "hdr", "smart"),
    "kulaklık": ("bağlantı", "anc", "mikrofon", "pil", "bluetooth", "ağırlık"),
}

def _section_meta(section_name: str) -> dict[str, Any]:
    normalized = (section_name or "Genel").strip().casefold()
    for key, meta in FEATURE_SECTION_META.items():
        if key in normalized:
            return meta
    return {"label": section_name or "Genel", "icon": "🔹", "order": 85}

def build_technical_feature_view(
    *,
    group: ProductGroup,
    feature_sections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Teknik özellikleri düzenli, özetlenebilir ve eksik veriye dayanıklı hale getirir."""
    known_names = {
        str(feature.get("name") or "").strip().casefold()
        for section in feature_sections
        for feature in section.get("features", [])
    }

    general_fallbacks = [
        ("Marka", group.brand),
        ("Model", group.model),
        ("Kategori", group.category),
    ]
    fallback_features = [
        {
            "id": None,
            "code": f"fallback_{name.casefold()}",
            "name": name,
            "value": str(value).strip(),
            "value_type": "text",
            "comparison_type": "neutral",
            "is_fallback": True,
        }
        for name, value in general_fallbacks
        if value and name.casefold() not in known_names
    ]

    sections = [
        {
            **section,
            "features": [dict(feature, is_fallback=feature.get("is_fallback", False)) for feature in section.get("features", [])],
        }
        for section in feature_sections
    ]
    if fallback_features:
        sections.insert(0, {"name": "Temel Bilgiler", "features": fallback_features})

    enriched_sections: list[dict[str, Any]] = []
    for section in sections:
        meta = _section_meta(section.get("name") or "Genel")
        enriched_sections.append({
            "name": meta["label"],
            "icon": meta["icon"],
            "order": meta["order"],
            "features": section.get("features", []),
        })

    enriched_sections.sort(key=lambda item: (item["order"], item["name"]))
    all_features = [feature for section in enriched_sections for feature in section["features"]]
    category = (group.category or "").strip().casefold()
    preferred_terms: tuple[str, ...] = ()
    for key, terms in CATEGORY_HEADLINE_FEATURES.items():
        if key in category:
            preferred_terms = terms
            break

    def feature_priority(feature: dict[str, Any]) -> tuple[int, str]:
        haystack = f"{feature.get('code') or ''} {feature.get('name') or ''}".casefold()
        for index, term in enumerate(preferred_terms):
            if term in haystack:
                return (index, str(feature.get("name") or ""))
        return (100, str(feature.get("name") or ""))

    headline_features = sorted(all_features, key=feature_priority)[:6]
    real_feature_count = sum(1 for feature in all_features if not feature.get("is_fallback"))
    section_count = len(enriched_sections)
    if real_feature_count >= 18:
        coverage_label, coverage_level = "Çok detaylı", "excellent"
    elif real_feature_count >= 10:
        coverage_label, coverage_level = "İyi", "good"
    elif real_feature_count >= 4:
        coverage_label, coverage_level = "Temel", "basic"
    else:
        coverage_label, coverage_level = "Geliştiriliyor", "limited"

    return {
        "sections": enriched_sections,
        "headline_features": headline_features,
        "feature_count": len(all_features),
        "real_feature_count": real_feature_count,
        "section_count": section_count,
        "coverage_label": coverage_label,
        "coverage_level": coverage_level,
    }

def _normalize_compare_display_value(
    *,
    feature_name: str,
    display_value: str,
    product_name: str = "",
) -> str:
    """Karşılaştırmada eski scraper birim hatalarını güvenli biçimde düzeltir.

    Özellikle bazı eski kayıtlarda 512 GB değerinin birimi yanlışlıkla TB olarak
    saklanmıştır. Ürün başlığında açıkça 512GB/512G geçiyorsa yalnızca gösterim
    katmanında düzeltilir; veritabanı değiştirilmez.
    """
    import re

    name = (feature_name or "").casefold()
    value = (display_value or "").strip()
    product = (product_name or "").casefold().replace(" ", "")

    if any(token in name for token in ("depolama", "storage", "ssd", "kapasite")):
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*tb", value, flags=re.I)
        if match:
            number = float(match.group(1).replace(",", "."))
            # 64/128/256/512 TB tüketici ürünlerinde gerçekçi değildir. Başlıkta
            # aynı kapasitenin GB/G biçimi geçiyorsa yanlış birimi düzeltiriz.
            integer = int(number) if number.is_integer() else None
            if integer in {64, 128, 256, 512} and (f"{integer}gb" in product or f"{integer}g" in product):
                return f"{integer} GB"
    return value


def _get_product_feature_map(
    *,
    db: Any,
    product_group_id: int,
) -> dict[str, dict[str, Any]]:
    """Karşılaştırma ekranı için özellikleri kod bazında hazırlar."""
    product_group = db.query(ProductGroup).filter(ProductGroup.id == product_group_id).first()
    product_name = product_group.canonical_name if product_group is not None else ""
    rows = (
        db.query(ProductFeature, ProductFeatureValue)
        .join(
            ProductFeatureValue,
            ProductFeatureValue.feature_id == ProductFeature.id,
        )
        .filter(
            ProductFeatureValue.product_group_id == product_group_id,
            or_(
                ProductFeature.is_active.is_(True),
                ProductFeature.is_active.is_(None),
            ),
        )
        .order_by(
            ProductFeature.section.asc(),
            ProductFeature.sort_order.asc(),
            ProductFeature.name.asc(),
        )
        .all()
    )

    feature_map: dict[str, dict[str, Any]] = {}

    for feature, value in rows:
        display_value = _format_feature_value(feature, value)
        if display_value is None:
            continue
        display_value = _normalize_compare_display_value(
            feature_name=feature.name or "",
            display_value=display_value,
            product_name=product_name,
        )

        raw_comparable: Any = None
        value_type = (feature.value_type or "text").strip().lower()

        if value_type == "number":
            raw_comparable = value.value_number
        elif value_type == "boolean":
            raw_comparable = value.value_boolean
        else:
            raw_comparable = (value.value_text or value.raw_value or "").strip().casefold()

        cleaned_name = _clean_feature_name(feature.name, display_value)
        section_name = (feature.section or "Genel").strip() or "Genel"

        # Bazı eski scraper kayıtlarında feature.code boş olabiliyor.
        # Kod yoksa bölüm + temiz özellik adı ile kararlı bir eşleştirme anahtarı üret.
        feature_code = (feature.code or "").strip()
        match_key = (
            f"code:{feature_code.casefold()}"
            if feature_code
            else f"name:{section_name.casefold()}::{cleaned_name.casefold()}"
        )

        feature_map[match_key] = {
            "code": feature_code or match_key,
            "name": cleaned_name,
            "section": section_name,
            "sort_order": feature.sort_order or 0,
            "display_value": display_value,
            "raw_value": raw_comparable,
            "value_type": value_type,
            "comparison_type": (feature.comparison_type or "neutral").strip().lower(),
        }

    return feature_map


def _determine_feature_winner(
    left_feature: dict[str, Any] | None,
    right_feature: dict[str, Any] | None,
) -> str | None:
    """Bir özellik satırında avantajlı tarafı belirler."""
    if left_feature is None or right_feature is None:
        return None

    left_value = left_feature.get("raw_value")
    right_value = right_feature.get("raw_value")
    comparison_type = left_feature.get("comparison_type", "neutral")

    if left_value is None or right_value is None or left_value == right_value:
        return None

    if comparison_type == "higher_better":
        return "left" if left_value > right_value else "right"

    if comparison_type == "lower_better":
        return "left" if left_value < right_value else "right"

    if comparison_type == "yes_better":
        return "left" if bool(left_value) else "right"

    if comparison_type == "no_better":
        return "left" if not bool(left_value) else "right"

    return None


def build_feature_comparison_rows(
    *,
    left_features: dict[str, dict[str, Any]],
    right_features: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """İki ürünün özelliklerini bölüm ve satır bazında birleştirir."""
    feature_codes = set(left_features) | set(right_features)
    rows: list[dict[str, Any]] = []

    for code in feature_codes:
        left_feature = left_features.get(code)
        right_feature = right_features.get(code)
        source = left_feature or right_feature
        if source is None:
            continue

        left_display = left_feature.get("display_value") if left_feature else None
        right_display = right_feature.get("display_value") if right_feature else None

        winner = _determine_feature_winner(left_feature, right_feature)
        is_equal = (
            left_display is not None
            and right_display is not None
            and left_display == right_display
        )
        comparison_type = source.get("comparison_type", "neutral")
        is_comparable = (
            left_feature is not None
            and right_feature is not None
            and comparison_type in {
                "higher_better",
                "lower_better",
                "yes_better",
                "no_better",
            }
        )

        loser = None
        if winner == "left":
            loser = "right"
        elif winner == "right":
            loser = "left"

        rows.append({
            "code": code,
            "name": source["name"],
            "section": source["section"],
            "sort_order": source["sort_order"],
            "left_value": left_display,
            "right_value": right_display,
            "is_different": left_display != right_display,
            "is_equal": is_equal,
            "is_comparable": is_comparable,
            "comparison_type": comparison_type,
            "winner": winner,
            "loser": loser,
        })

    rows.sort(key=lambda row: (row["section"], row["sort_order"], row["name"]))

    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in rows:
        grouped.setdefault(row["section"], []).append(row)

    return [
        {
            "name": section_name,
            "rows": section_rows,
            "different_count": sum(
                1
                for row in section_rows
                if row["is_different"]
            ),
        }
        for section_name, section_rows in grouped.items()
    ]



@router.get(
    "",
    response_class=HTMLResponse,
)
@router.get(
    "/",
    response_class=HTMLResponse,
)
def product_groups_dashboard(
    request: Request,
    search: Optional[str] = Query(
        default=None,
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=5,
        le=100,
    ),
):
    db = SessionLocal()

    try:
        query = db.query(
            ProductGroup
        )

        cleaned_search = (
            search.strip()
            if search
            else ""
        )

        if cleaned_search:
            search_pattern = (
                f"%{cleaned_search}%"
            )

            query = query.filter(
                or_(
                    ProductGroup.canonical_name.ilike(
                        search_pattern
                    ),
                    ProductGroup.normalized_name.ilike(
                        search_pattern
                    ),
                    ProductGroup.brand.ilike(
                        search_pattern
                    ),
                    ProductGroup.model.ilike(
                        search_pattern
                    ),
                    ProductGroup.category.ilike(
                        search_pattern
                    ),
                    ProductGroup.identity_source.ilike(
                        search_pattern
                    ),
                )
            )

        total_groups = query.count()

        total_pages = max(
            1,
            (
                total_groups
                + page_size
                - 1
            )
            // page_size,
        )

        if page > total_pages:
            page = total_pages

        offset = (
            page - 1
        ) * page_size

        groups = (
            query
            .order_by(
                ProductGroup.updated_at.desc(),
                ProductGroup.id.desc(),
            )
            .offset(offset)
            .limit(page_size)
            .all()
        )

        product_groups: list[
            dict[str, Any]
        ] = []

        total_available_offers = 0
        groups_with_multiple_stores = 0
        total_saving_amount = 0.0

        for group in groups:
            comparison = (
                get_product_comparison(
                    db=db,
                    identity_key=group.group_key,
                )
            )

            if comparison is None:
                continue

            offer_count = int(
                comparison.get(
                    "offer_count",
                    0,
                )
                or 0
            )

            total_offer_count = int(
                comparison.get(
                    "total_offer_count",
                    0,
                )
                or 0
            )

            saving_amount = float(
                comparison.get(
                    "saving_amount",
                    0,
                )
                or 0
            )

            saving_percent = float(
                comparison.get(
                    "saving_percent",
                    0,
                )
                or 0
            )

            total_available_offers += (
                offer_count
            )

            total_saving_amount += (
                saving_amount
            )

            if offer_count > 1:
                groups_with_multiple_stores += 1

            product_groups.append(
                {
                    "id": group.id,
                    "identity_key": (
                        group.group_key
                    ),
                    "identity_source": (
                        group.identity_source
                    ),
                    "product_name": (
                        group.canonical_name
                    ),
                    "brand": group.brand,
                    "model": group.model,
                    "category": group.category,
                    "image": group.image,
                    "offer_count": (
                        offer_count
                    ),
                    "total_offer_count": (
                        total_offer_count
                    ),
                    "best_price": (
                        comparison.get(
                            "best_price"
                        )
                    ),
                    "highest_price": (
                        comparison.get(
                            "highest_price"
                        )
                    ),
                    "saving_amount": round(
                        saving_amount,
                        2,
                    ),
                    "saving_percent": round(
                        saving_percent,
                        2,
                    ),
                    "best_store": (
                        comparison.get(
                            "best_store"
                        )
                    ),
                    "updated_at": (
                        group.updated_at
                    ),
                }
            )

        average_offer_count = (
            round(
                total_available_offers
                / len(product_groups),
                1,
            )
            if product_groups
            else 0
        )

        return templates.TemplateResponse(
            request=request,
            name="product_groups.html",
            context={
                "product_groups": (
                    product_groups
                ),
                "search": cleaned_search,
                "page": page,
                "page_size": page_size,
                "total_pages": (
                    total_pages
                ),
                "total_groups": (
                    total_groups
                ),
                "visible_group_count": len(
                    product_groups
                ),
                "total_available_offers": (
                    total_available_offers
                ),
                "average_offer_count": (
                    average_offer_count
                ),
                "groups_with_multiple_stores": (
                    groups_with_multiple_stores
                ),
                "total_saving_amount": round(
                    total_saving_amount,
                    2,
                ),
            },
        )

    finally:
        db.close()


@router.get(
    "/compare",
    response_class=HTMLResponse,
)
def compare_product_groups(
    request: Request,
    products: list[str] = Query(default=[]),
    left: Optional[str] = Query(default=None),
    right: Optional[str] = Query(default=None),
):
    db = SessionLocal()
    try:
        candidate_groups = (
            db.query(ProductGroup)
            .order_by(ProductGroup.category.asc(), ProductGroup.brand.asc(), ProductGroup.canonical_name.asc())
            .all()
        )
        selected_keys = normalize_selected_keys(products, left, right)
        selected_groups = []
        for key in selected_keys:
            group = db.query(ProductGroup).filter(ProductGroup.group_key == key).first()
            if group is not None:
                selected_groups.append(group)
        feature_maps = [
            _get_product_feature_map(db=db, product_group_id=group.id)
            for group in selected_groups
        ]
        summaries = [
            get_product_comparison(db=db, identity_key=group.group_key)
            for group in selected_groups
        ]
        comparison_sections = build_comparison_matrix(feature_maps) if len(selected_groups) >= 2 else []
        product_metrics = build_product_metrics(selected_groups, summaries, comparison_sections) if len(selected_groups) >= 2 else []
        flat_rows = [row for section in comparison_sections for row in section["rows"]]
        return templates.TemplateResponse(
            request=request,
            name="product_group_compare_v2.html",
            context={
                "candidate_groups": candidate_groups,
                "selected_keys": [g.group_key for g in selected_groups],
                "selected_groups": selected_groups,
                "product_metrics": product_metrics,
                "comparison_sections": comparison_sections,
                "total_feature_count": len(flat_rows),
                "different_feature_count": sum(1 for row in flat_rows if row["is_different"]),
                "equal_feature_count": sum(1 for row in flat_rows if row["is_equal"]),
                "comparison_v2_version": COMPARISON_V2_VERSION,
                "max_products": 4,
            },
        )
    finally:
        db.close()



@router.get(
    "/{identity_key}",
    response_class=HTMLResponse,
)
def product_group_detail(
    request: Request,
    identity_key: str,
    variant: int | None = None,
    firsat_session: str | None = Cookie(default=None),
):
    db = SessionLocal()

    try:
        group = (
            db.query(
                ProductGroup
            )
            .filter(
                ProductGroup.group_key
                == identity_key
            )
            .first()
        )

        # Eski admin bağlantıları ürün kimliğini sayısal olarak gönderebiliyordu.
        # Ürün kaydının bağlı olduğu grubu bularak bu bağlantıları geriye dönük destekle.
        if group is None and identity_key.isdigit():
            offer = (
                db.query(ProductOffer)
                .filter(ProductOffer.product_id == int(identity_key))
                .first()
            )
            if offer is not None:
                group = (
                    db.query(ProductGroup)
                    .filter(ProductGroup.id == offer.group_id)
                    .first()
                )

        global_product = (
            db.query(GlobalProduct)
            .filter(GlobalProduct.identity_key == identity_key)
            .first()
        )

        if group is None and global_product is not None:
            group = (
                db.query(ProductGroup)
                .filter(
                    ProductGroup.group_key
                    == global_product.identity_key
                )
                .first()
            )

        if group is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Ürün grubu bulunamadı."
                ),
            )

        user = _current_user(db, firsat_session)
        if user is not None:
            recent = (
                db.query(RecentlyViewed)
                .filter(
                    RecentlyViewed.user_id == user.id,
                    RecentlyViewed.product_group_id == group.id,
                )
                .first()
            )
            if recent is None:
                recent = RecentlyViewed(user_id=user.id, product_group_id=group.id)
                db.add(recent)
            else:
                recent.viewed_at = datetime.utcnow()
            db.commit()

        legacy_comparison = (
            get_product_comparison(
                db=db,
                identity_key=group.group_key,
            )
        )
        global_comparison = get_global_product_comparison(
            db=db,
            identity_key=group.group_key,
            selected_variant_id=variant,
        )
        comparison = global_comparison or legacy_comparison

        # V21.2: Akakce/Cimri tipi katalog-first teklif katmani mevcut
        # urun detay sayfasina dogrudan baglanir. Bu okuma canli scrape baslatmaz.
        price_comparison_core = None
        if global_product is not None:
            selected_global_variant_id = (
                global_comparison.get("selected_variant_id")
                if global_comparison
                else None
            )
            price_comparison_core = get_product_price_comparison(
                db=db,
                global_product_id=global_product.id,
                stale_hours=6,
                global_variant_id=selected_global_variant_id,
            )
            if price_comparison_core is not None and comparison is not None:
                comparison = dict(comparison)
                core_summary = price_comparison_core.get("summary", {})
                comparison.update({
                    "offers": price_comparison_core.get("offers", []),
                    "offer_count": core_summary.get("offer_count", 0),
                    "store_count": core_summary.get("store_count", 0),
                    "best_price": core_summary.get("best_price"),
                    "highest_price": core_summary.get("highest_price"),
                    "saving_amount": core_summary.get("saving_amount", 0.0),
                    "saving_percent": core_summary.get("saving_percent", 0.0),
                    "best_store": core_summary.get("best_store"),
                    "best_offer": price_comparison_core.get("best_offer"),
                    "data_source": "price_comparison_core_v21_2",
                    "global_product_id": global_product.id,
                    "price_comparison_mode": price_comparison_core.get("data_mode"),
                    "price_comparison_summary": core_summary,
                })

        if comparison is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Ürün karşılaştırma bilgisi "
                    "bulunamadı."
                ),
            )

        legacy_history_data = (
            get_product_price_history(
                db=db,
                identity_key=group.group_key,
            )
        )
        global_history_data = get_global_price_history(
            db=db,
            identity_key=group.group_key,
            selected_variant_id=(
                comparison.get("selected_variant_id")
                if comparison.get("global_product_id")
                else None
            ),
        )
        history_data = (
            global_history_data
            if (
                global_history_data
                and global_history_data.get("price_record_count", 0) > 0
            )
            else legacy_history_data
        )

        if history_data is None:
            history_data = {
                "identity_key": (
                    identity_key
                ),
                "product_name": (
                    group.canonical_name
                ),
                "store_count": 0,
                "price_record_count": 0,
                "lowest_price": None,
                "highest_price": None,
                "average_price": None,
                "stores": [],
            }

        ai_analysis = (
            build_ai_comparison_analysis(
                comparison=comparison,
                history_data=history_data,
            )
        )

        chart_labels, chart_datasets = (
            build_chart_datasets(
                history_data=history_data,
            )
        )

        deal_badge = build_deal_badge(
            comparison=comparison,
            history_data=history_data,
        )

        price_analysis = build_price_analysis(
            db=db,
            identity_key=group.group_key,
        ) or {}

        deal_intelligence_v13 = build_deal_intelligence_v13(
            price_analysis=price_analysis,
            ai_analysis=ai_analysis,
            comparison=comparison,
        )

        feature_sections = get_grouped_product_features(
            db=db,
            product_group_id=group.id,
        )
        technical_feature_view = build_technical_feature_view(
            group=group,
            feature_sections=feature_sections,
        )

        offers = comparison.get(
            "offers",
            [],
        )

        core_has_fresh_offers = bool(
            price_comparison_core
            and price_comparison_core.get("summary", {}).get("fresh_offer_count")
        )
        available_offers = sorted(
            [
                offer
                for offer in offers
                if offer.get(
                    "is_available"
                )
            ],
            key=lambda offer: (
                (0 if offer.get("freshness_code") == "FRESH" else 1)
                if core_has_fresh_offers
                else 0,
                float(offer.get("total_price") or float("inf")),
                str(offer.get("store") or ""),
            ),
        )

        unavailable_offers = [
            offer
            for offer in offers
            if not offer.get(
                "is_available"
            )
        ]

        for offer in available_offers + unavailable_offers:
            offer["logo_url"] = resolve_store_logo(
                offer.get("store_code"),
                offer.get("store"),
            )
            offer.update(build_offer_status(offer))

        best_offer = available_offers[0] if available_offers else None

        purchase_assistant = build_ai_purchase_assistant(
            comparison=comparison,
            history_data=history_data,
            ai_analysis=ai_analysis,
            group=group,
            feature_headlines=technical_feature_view["headline_features"],
        )

        alternatives = get_product_alternatives(
            db=db,
            current_group=group,
            current_comparison=comparison,
            limit=4,
        )

        community = get_product_community(db, group.id, user.id if user else None)

        smart_recommendations = get_smart_recommendations(
            db=db,
            current_group=group,
            current_comparison=comparison,
            per_bucket=4,
        )

        product_gallery = build_product_gallery(db, group)

        return templates.TemplateResponse(
            request=request,
            name="product_group_detail_v4.html",
            context={
    "group": group,
    "comparison": comparison,
    "history_data": history_data,
    "ai_analysis": ai_analysis,
    "available_offers": (
        available_offers
    ),
    "best_offer": best_offer,
    "unavailable_offers": (
        unavailable_offers
    ),
    "chart_labels": chart_labels,
    "chart_datasets": (
        chart_datasets
    ),
    "deal_badge": deal_badge,
    "price_analysis": price_analysis,
    "deal_intelligence_v13": deal_intelligence_v13,
    "purchase_assistant": purchase_assistant,
    "alternatives": alternatives,
    "smart_recommendations": smart_recommendations,
    "community": community,
    "product_gallery": product_gallery,
    "current_user": user,
    "comparison_data_source": comparison.get("data_source", "legacy"),
    "price_comparison_core": price_comparison_core,
    "feature_sections": technical_feature_view["sections"],
    "feature_headlines": technical_feature_view["headline_features"],
    "feature_count": technical_feature_view["feature_count"],
    "real_feature_count": technical_feature_view["real_feature_count"],
    "feature_section_count": technical_feature_view["section_count"],
    "feature_coverage_label": technical_feature_view["coverage_label"],
    "feature_coverage_level": technical_feature_view["coverage_level"],
    "canonical_url": canonical_product_url(request.base_url, group.canonical_name, group.group_key),
    "seo_title": f"{group.canonical_name} Fiyatları ve Karşılaştırma | FırsatAI",
    "seo_description": f"{group.canonical_name} güncel fiyatlarını, mağaza tekliflerini, fiyat geçmişini ve teknik özelliklerini karşılaştırın.",
    "seo_product_path": product_url(group.canonical_name, group.group_key),
    "website_schema_json": schema_dumps(website_schema(request.base_url)),
    "breadcrumb_schema_json": schema_dumps(
        breadcrumb_schema(
            request.base_url,
            [
                ("Ana sayfa", "/"),
                (str(getattr(group, "category", None) or "Ürünler"), f"/arama?q={getattr(group, 'category', None) or ''}"),
                (group.canonical_name, product_url(group.canonical_name, group.group_key)),
            ],
        )
    ),
    "product_schema_json": schema_dumps(
        product_schema(
            base_url=request.base_url,
            canonical_url=canonical_product_url(request.base_url, group.canonical_name, group.group_key),
            group=group,
            comparison=comparison,
            available_offers=available_offers,
            image_urls=product_gallery,
            description=f"{group.canonical_name} güncel fiyatları, mağaza teklifleri ve teknik özellikleri.",
        )
    ),
},
        )

    finally:
        db.close()