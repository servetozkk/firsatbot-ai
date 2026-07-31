from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
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
    ProductFeatureValue,
    ProductGroup,
)
from app.services.ai_comparison_service import (
    build_ai_comparison_analysis,
)
from app.services.comparison_service import (
    get_product_comparison,
)
from app.services.history_service import (
    get_product_price_history,
)
from app.services.price_analysis_service import build_price_analysis

router = APIRouter(
    prefix="/karsilastir",
    tags=["Müşteri Ürün Karşılaştırma"],
)


BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates"),
)


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


def _get_product_feature_map(
    *,
    db: Any,
    product_group_id: int,
) -> dict[str, dict[str, Any]]:
    """Karşılaştırma ekranı için özellikleri kod bazında hazırlar."""
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
    left: Optional[str] = Query(default=None),
    right: Optional[str] = Query(default=None),
):
    db = SessionLocal()

    try:
        candidate_groups = (
            db.query(ProductGroup)
            .order_by(
                ProductGroup.category.asc(),
                ProductGroup.brand.asc(),
                ProductGroup.canonical_name.asc(),
            )
            .all()
        )

        left_group = None
        right_group = None

        if left:
            left_group = (
                db.query(ProductGroup)
                .filter(ProductGroup.group_key == left)
                .first()
            )

        if right:
            right_group = (
                db.query(ProductGroup)
                .filter(ProductGroup.group_key == right)
                .first()
            )

        comparison_sections: list[dict[str, Any]] = []
        left_summary = None
        right_summary = None

        total_feature_count = 0
        different_feature_count = 0
        equal_feature_count = 0
        comparable_feature_count = 0
        left_win_count = 0
        right_win_count = 0

        left_advantage_percent = 0
        right_advantage_percent = 0
        general_winner = None
        general_winner_name = None
        price_winner = None

        if left_group and right_group:
            left_features = _get_product_feature_map(
                db=db,
                product_group_id=left_group.id,
            )
            right_features = _get_product_feature_map(
                db=db,
                product_group_id=right_group.id,
            )

            comparison_sections = build_feature_comparison_rows(
                left_features=left_features,
                right_features=right_features,
            )

            flat_rows = [
                row
                for section in comparison_sections
                for row in section["rows"]
            ]

            total_feature_count = len(flat_rows)
            different_feature_count = sum(
                1
                for row in flat_rows
                if row["is_different"]
            )
            equal_feature_count = sum(
                1
                for row in flat_rows
                if row["is_equal"]
            )
            comparable_feature_count = sum(
                1
                for row in flat_rows
                if row["is_comparable"]
            )
            left_win_count = sum(
                1
                for row in flat_rows
                if row["winner"] == "left"
            )
            right_win_count = sum(
                1
                for row in flat_rows
                if row["winner"] == "right"
            )

            decided_feature_count = left_win_count + right_win_count
            if decided_feature_count:
                left_advantage_percent = round(
                    left_win_count / decided_feature_count * 100,
                    1,
                )
                right_advantage_percent = round(
                    right_win_count / decided_feature_count * 100,
                    1,
                )

            if left_win_count > right_win_count:
                general_winner = "left"
                general_winner_name = left_group.canonical_name
            elif right_win_count > left_win_count:
                general_winner = "right"
                general_winner_name = right_group.canonical_name
            elif comparable_feature_count > 0:
                general_winner = "draw"
                general_winner_name = "Berabere"

            left_summary = get_product_comparison(
                db=db,
                identity_key=left_group.group_key,
            )
            right_summary = get_product_comparison(
                db=db,
                identity_key=right_group.group_key,
            )

            left_price = (
                left_summary.get("best_price")
                if left_summary
                else None
            )
            right_price = (
                right_summary.get("best_price")
                if right_summary
                else None
            )

            if left_price is not None and right_price is not None:
                if left_price < right_price:
                    price_winner = "left"
                elif right_price < left_price:
                    price_winner = "right"

        return templates.TemplateResponse(
            request=request,
            name="product_group_compare.html",
            context={
                "candidate_groups": candidate_groups,
                "left_key": left or "",
                "right_key": right or "",
                "left_group": left_group,
                "right_group": right_group,
                "left_summary": left_summary,
                "right_summary": right_summary,
                "comparison_sections": comparison_sections,
                "total_feature_count": total_feature_count,
                "different_feature_count": different_feature_count,
                "equal_feature_count": equal_feature_count,
                "comparable_feature_count": comparable_feature_count,
                "left_win_count": left_win_count,
                "right_win_count": right_win_count,
                "left_advantage_percent": left_advantage_percent,
                "right_advantage_percent": right_advantage_percent,
                "general_winner": general_winner,
                "general_winner_name": general_winner_name,
                "price_winner": price_winner,
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

        if group is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Ürün grubu bulunamadı."
                ),
            )

        comparison = (
            get_product_comparison(
                db=db,
                identity_key=identity_key,
            )
        )

        if comparison is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Ürün karşılaştırma bilgisi "
                    "bulunamadı."
                ),
            )

        history_data = (
            get_product_price_history(
                db=db,
                identity_key=identity_key,
            )
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
            identity_key=identity_key,
        ) or {}

        feature_sections = get_grouped_product_features(
            db=db,
            product_group_id=group.id,
        )

        offers = comparison.get(
            "offers",
            [],
        )

        available_offers = [
            offer
            for offer in offers
            if offer.get(
                "is_available"
            )
        ]

        unavailable_offers = [
            offer
            for offer in offers
            if not offer.get(
                "is_available"
            )
        ]

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
    "unavailable_offers": (
        unavailable_offers
    ),
    "chart_labels": chart_labels,
    "chart_datasets": (
        chart_datasets
    ),
    "deal_badge": deal_badge,
    "price_analysis": price_analysis,
    "feature_sections": feature_sections,
    "feature_count": sum(
        len(section["features"])
        for section in feature_sections
    ),
},
        )

    finally:
        db.close()