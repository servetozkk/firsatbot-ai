import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_

from app.database.database import SessionLocal
from app.database.models import DeletedProduct, OfferPriceHistory, PriceHistory, ProductDB, ProductOffer
from app.services.data_integrity_service import record_admin_action, stable_product_key
from app.services.scan_service import (
    validate_product_url,
    get_cross_store_scan_task,
)
from app.services.production_ingestion_v220_service import (
    start_production_ingestion,
    get_ingestion_task,
)


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

BASE_DIR = Path(__file__).resolve().parent.parent

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


def calculate_discount(
    current_price: Optional[float],
    old_price: Optional[float],
) -> float:
    """
    GÃ¼ncel fiyat ile eski fiyat arasÄ±ndaki indirim oranÄ±nÄ± hesaplar.
    """

    current = float(current_price or 0)
    previous = float(old_price or 0)

    if previous <= 0:
        return 0

    if current >= previous:
        return 0

    discount = (
        (previous - current)
        / previous
        * 100
    )

    return round(discount, 1)


def normalize_specification_name(
    name: Any,
    value: Any,
) -> str:
    """
    BazÄ± maÄŸaza sayfalarÄ±nda Ã¶zellik etiketi ve deÄŸeri aynÄ±
    DOM dÃ¼ÄŸÃ¼mÃ¼nden alÄ±ndÄ±ÄŸÄ± iÃ§in anahtar ÅŸu ÅŸekilde gelebilir:

        Kapasite1 TB -> 1 TB

    Åablonda deÄŸerin iki kez gÃ¶rÃ¼nmesini Ã¶nlemek iÃ§in anahtarÄ±n
    sonuna yapÄ±ÅŸmÄ±ÅŸ olan deÄŸeri gÃ¼venli biÃ§imde kaldÄ±rÄ±r.
    """

    cleaned_name = str(name or "Ã–zellik").strip()
    cleaned_value = str(value or "").strip()

    if not cleaned_value:
        return cleaned_name or "Ã–zellik"

    if cleaned_name.casefold().endswith(cleaned_value.casefold()):
        candidate = cleaned_name[:-len(cleaned_value)].strip()
        candidate = candidate.rstrip(":-â€“â€”|/").strip()

        if candidate:
            return candidate

    return cleaned_name or "Ã–zellik"


def parse_specifications(
    raw_specifications: Optional[str],
) -> list[dict[str, str]]:
    """
    Teknik Ã¶zellikleri JSON veya dÃ¼z metin formatÄ±ndan
    ÅŸablonda kullanÄ±labilecek listeye dÃ¶nÃ¼ÅŸtÃ¼rÃ¼r.

    Desteklenen Ã¶rnekler:

    JSON:
    {
        "Ä°ÅŸlemci": "Ryzen 7",
        "RAM": "16 GB"
    }

    DÃ¼z metin:
    Ä°ÅŸlemci: Ryzen 7
    RAM: 16 GB
    """

    if not raw_specifications:
        return []

    cleaned_value = raw_specifications.strip()

    if not cleaned_value:
        return []

    try:
        parsed_json: Any = json.loads(cleaned_value)

        if isinstance(parsed_json, dict):
            return [
                {
                    "name": normalize_specification_name(
                        key,
                        value,
                    ),
                    "value": str(value).strip(),
                }
                for key, value in parsed_json.items()
            ]

        if isinstance(parsed_json, list):
            parsed_items: list[dict[str, str]] = []

            for item in parsed_json:
                if isinstance(item, dict):
                    name = (
                        item.get("name")
                        or item.get("key")
                        or item.get("title")
                        or item.get("label")
                        or "Ã–zellik"
                    )

                    value = (
                        item.get("value")
                        or item.get("description")
                        or item.get("text")
                        or "-"
                    )

                    parsed_items.append(
                        {
                            "name": normalize_specification_name(
                                name,
                                value,
                            ),
                            "value": str(value).strip(),
                        }
                    )

                else:
                    parsed_items.append(
                        {
                            "name": "Ã–zellik",
                            "value": str(item),
                        }
                    )

            return parsed_items

    except (json.JSONDecodeError, TypeError):
        pass

    specification_items: list[dict[str, str]] = []

    normalized_text = cleaned_value.replace(
        " | ",
        "\n",
    )

    for line in normalized_text.splitlines():
        cleaned_line = line.strip(" -â€¢\t")

        if not cleaned_line:
            continue

        if ":" in cleaned_line:
            name, value = cleaned_line.split(
                ":",
                1,
            )

            specification_items.append(
                {
                    "name": name.strip(),
                    "value": value.strip(),
                }
            )

        elif "=" in cleaned_line:
            name, value = cleaned_line.split(
                "=",
                1,
            )

            specification_items.append(
                {
                    "name": name.strip(),
                    "value": value.strip(),
                }
            )

        else:
            specification_items.append(
                {
                    "name": "Ã–zellik",
                    "value": cleaned_line,
                }
            )

    return specification_items


def build_ai_reasons(
    product: ProductDB,
    discount: float,
    history_prices: list[float],
) -> list[dict[str, str]]:
    """
    ÃœrÃ¼nÃ¼n mevcut bilgilerine gÃ¶re aÃ§Ä±klayÄ±cÄ± AI deÄŸerlendirmeleri Ã¼retir.
    """

    reasons: list[dict[str, str]] = []

    ai_score = int(product.ai_score or 0)

    if ai_score >= 80:
        reasons.append(
            {
                "type": "success",
                "title": "YÃ¼ksek fÄ±rsat puanÄ±",
                "description": (
                    f"Bu Ã¼rÃ¼nÃ¼n AI fÄ±rsat puanÄ± {ai_score}/100."
                ),
            }
        )

    elif ai_score >= 50:
        reasons.append(
            {
                "type": "warning",
                "title": "Orta seviye fÄ±rsat puanÄ±",
                "description": (
                    f"Bu Ã¼rÃ¼nÃ¼n AI fÄ±rsat puanÄ± {ai_score}/100."
                ),
            }
        )

    else:
        reasons.append(
            {
                "type": "secondary",
                "title": "DÃ¼ÅŸÃ¼k fÄ±rsat puanÄ±",
                "description": (
                    f"Bu Ã¼rÃ¼nÃ¼n AI fÄ±rsat puanÄ± {ai_score}/100."
                ),
            }
        )

    if discount >= 20:
        reasons.append(
            {
                "type": "success",
                "title": "GÃ¼Ã§lÃ¼ indirim",
                "description": (
                    f"ÃœrÃ¼nde yaklaÅŸÄ±k %{discount:.1f} indirim bulunuyor."
                ),
            }
        )

    elif discount > 0:
        reasons.append(
            {
                "type": "info",
                "title": "Fiyat indirimi",
                "description": (
                    f"ÃœrÃ¼n Ã¶nceki fiyatÄ±na gÃ¶re %{discount:.1f} daha ucuz."
                ),
            }
        )

    if history_prices:
        lowest_price = min(history_prices)
        current_price = float(product.price or 0)

        if current_price <= lowest_price:
            reasons.append(
                {
                    "type": "success",
                    "title": "Takip edilen en dÃ¼ÅŸÃ¼k fiyat",
                    "description": (
                        "GÃ¼ncel fiyat, kayÄ±tlÄ± fiyat geÃ§miÅŸindeki "
                        "en dÃ¼ÅŸÃ¼k seviyede."
                    ),
                }
            )

        average_price = (
            sum(history_prices)
            / len(history_prices)
        )

        if current_price < average_price:
            difference_percentage = (
                (average_price - current_price)
                / average_price
                * 100
            )

            reasons.append(
                {
                    "type": "success",
                    "title": "Ortalama fiyatÄ±n altÄ±nda",
                    "description": (
                        "GÃ¼ncel fiyat, kayÄ±tlÄ± ortalama fiyatÄ±n "
                        f"yaklaÅŸÄ±k %{difference_percentage:.1f} altÄ±nda."
                    ),
                }
            )

    if product.rating is not None:
        rating = float(product.rating)

        if rating >= 4.5:
            reasons.append(
                {
                    "type": "success",
                    "title": "YÃ¼ksek kullanÄ±cÄ± puanÄ±",
                    "description": (
                        f"ÃœrÃ¼nÃ¼n kullanÄ±cÄ± puanÄ± {rating:.1f}/5."
                    ),
                }
            )

        elif rating >= 4:
            reasons.append(
                {
                    "type": "info",
                    "title": "Olumlu kullanÄ±cÄ± puanÄ±",
                    "description": (
                        f"ÃœrÃ¼nÃ¼n kullanÄ±cÄ± puanÄ± {rating:.1f}/5."
                    ),
                }
            )

    if product.review_count is not None:
        review_count = int(product.review_count)

        if review_count >= 1000:
            reasons.append(
                {
                    "type": "success",
                    "title": "YÃ¼ksek yorum sayÄ±sÄ±",
                    "description": (
                        f"ÃœrÃ¼n iÃ§in {review_count:,} kullanÄ±cÄ± yorumu bulunuyor."
                    ).replace(",", "."),
                }
            )

        elif review_count >= 100:
            reasons.append(
                {
                    "type": "info",
                    "title": "Yeterli kullanÄ±cÄ± geri bildirimi",
                    "description": (
                        f"ÃœrÃ¼n iÃ§in {review_count} kullanÄ±cÄ± yorumu bulunuyor."
                    ),
                }
            )

    if product.last_notified_price is not None:
        reasons.append(
            {
                "type": "primary",
                "title": "Telegram bildirimi gÃ¶nderildi",
                "description": (
                    "Bu Ã¼rÃ¼n daha Ã¶nce fÄ±rsat bildirimi olarak gÃ¶nderilmiÅŸ."
                ),
            }
        )

    if not reasons:
        reasons.append(
            {
                "type": "secondary",
                "title": "Yeterli veri bulunmuyor",
                "description": (
                    "AyrÄ±ntÄ±lÄ± fÄ±rsat analizi iÃ§in daha fazla fiyat "
                    "ve Ã¼rÃ¼n bilgisi gerekiyor."
                ),
            }
        )

    return reasons


@router.get(
    "",
    response_class=HTMLResponse,
)
@router.get(
    "/",
    response_class=HTMLResponse,
)
def admin_dashboard(
    request: Request,
):
    db = SessionLocal()

    try:
        all_products = (
            db.query(ProductDB)
            .order_by(ProductDB.id.desc())
            .all()
        )

        total_products = len(all_products)

        total_history = db.query(
            PriceHistory
        ).count()

        latest_products = all_products[:10]

        notified_products = sum(
            1
            for product in all_products
            if product.last_notified_price is not None
        )

        products_with_score = [
            product
            for product in all_products
            if product.ai_score is not None
        ]

        scores = [
            float(product.ai_score or 0)
            for product in products_with_score
        ]

        average_ai_score = (
            round(
                sum(scores) / len(scores),
                1,
            )
            if scores
            else 0
        )

        highest_ai_score = (
            round(max(scores), 1)
            if scores
            else 0
        )

        high_score_count = sum(
            1
            for score in scores
            if score >= 80
        )

        score_distribution = {
            "low": sum(
                1
                for score in scores
                if score < 50
            ),
            "medium": sum(
                1
                for score in scores
                if 50 <= score < 80
            ),
            "high": sum(
                1
                for score in scores
                if score >= 80
            ),
        }

        discount_rows: list[dict[str, Any]] = []

        for product in all_products:
            discount = calculate_discount(
                current_price=product.price,
                old_price=product.old_price,
            )

            if discount <= 0:
                continue

            discount_rows.append(
                {
                    "product": product,
                    "discount": discount,
                }
            )

        discount_values = [
            row["discount"]
            for row in discount_rows
        ]

        average_discount = (
            round(
                sum(discount_values)
                / len(discount_values),
                1,
            )
            if discount_values
            else 0
        )

        best_discount = (
            round(max(discount_values), 1)
            if discount_values
            else 0
        )

        top_ai_products = sorted(
            products_with_score,
            key=lambda product: float(
                product.ai_score or 0
            ),
            reverse=True,
        )[:5]

        best_discount_products = sorted(
            discount_rows,
            key=lambda row: row["discount"],
            reverse=True,
        )[:5]

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "total_products": total_products,
                "total_history": total_history,
                "notified_products": notified_products,
                "average_ai_score": average_ai_score,
                "highest_ai_score": highest_ai_score,
                "high_score_count": high_score_count,
                "average_discount": average_discount,
                "best_discount": best_discount,
                "score_distribution": score_distribution,
                "latest_products": latest_products,
                "top_ai_products": top_ai_products,
                "best_discount_products": best_discount_products,
            },
        )

    finally:
        db.close()

@router.get(
    "/products",
    response_class=HTMLResponse,
)
def admin_products(
    request: Request,
    search: Optional[str] = Query(default=None),
    minimum_score: Optional[float] = Query(default=None),
    notified: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    seller: Optional[str] = Query(default=None),
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=5, le=100),
):
    db = SessionLocal()

    try:
        category_options = [
            row[0]
            for row in db.query(ProductDB.category)
            .filter(ProductDB.category.isnot(None), ProductDB.category != "")
            .distinct()
            .order_by(ProductDB.category.asc())
            .all()
            if row[0]
        ]
        seller_options = [
            row[0]
            for row in db.query(ProductDB.seller)
            .filter(ProductDB.seller.isnot(None), ProductDB.seller != "")
            .distinct()
            .order_by(ProductDB.seller.asc())
            .limit(50)
            .all()
            if row[0]
        ]

        query = db.query(ProductDB)
        cleaned_search = search.strip() if search else None
        cleaned_category = category.strip() if category else None
        cleaned_seller = seller.strip() if seller else None

        if cleaned_search:
            search_pattern = f"%{cleaned_search}%"
            query = query.filter(or_(
                ProductDB.name.ilike(search_pattern),
                ProductDB.seller.ilike(search_pattern),
                ProductDB.url.ilike(search_pattern),
                ProductDB.brand.ilike(search_pattern),
                ProductDB.model.ilike(search_pattern),
                ProductDB.category.ilike(search_pattern),
            ))

        if minimum_score is not None:
            query = query.filter(ProductDB.ai_score >= minimum_score)
        if notified == "yes":
            query = query.filter(ProductDB.last_notified_price.isnot(None))
        elif notified == "no":
            query = query.filter(ProductDB.last_notified_price.is_(None))
        if cleaned_category:
            query = query.filter(ProductDB.category == cleaned_category)
        if cleaned_seller:
            query = query.filter(ProductDB.seller == cleaned_seller)

        total_products = query.count()
        total_pages = max(1, (total_products + page_size - 1) // page_size)
        page = min(page, total_pages)
        offset = (page - 1) * page_size

        if sort == "price_asc":
            query = query.order_by(ProductDB.price.asc(), ProductDB.id.desc())
        elif sort == "price_desc":
            query = query.order_by(ProductDB.price.desc(), ProductDB.id.desc())
        elif sort == "score_desc":
            query = query.order_by(ProductDB.ai_score.desc(), ProductDB.id.desc())
        elif sort == "discount":
            query = query.order_by((ProductDB.old_price - ProductDB.price).desc(), ProductDB.id.desc())
        else:
            query = query.order_by(ProductDB.id.desc())

        products = query.offset(offset).limit(page_size).all()

        return templates.TemplateResponse(
            request=request,
            name="products.html",
            context={
                "products": products,
                "search": cleaned_search or "",
                "minimum_score": minimum_score if minimum_score is not None else "",
                "notified": notified or "",
                "category": cleaned_category or "",
                "seller": cleaned_seller or "",
                "sort": sort,
                "category_options": category_options,
                "seller_options": seller_options,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_products": total_products,
            },
        )
    finally:
        db.close()


def _delete_product_records(db, product_ids: list[int]) -> int:
    """Ürünleri soft-delete yapar ve bütün scraper girişlerinde kalıcı olarak engeller."""
    cleaned_ids = sorted({int(value) for value in product_ids if int(value) > 0})
    if not cleaned_ids:
        return 0

    rows = (db.query(ProductDB)
            .execution_options(include_deleted=True)
            .filter(ProductDB.id.in_(cleaned_ids)).all())
    now = datetime.utcnow()
    changed = 0
    for item in rows:
        offer = db.query(ProductOffer).filter(ProductOffer.product_id == item.id).first()
        identity_key = None
        if offer is not None:
            try:
                from app.database.models import ProductGroup
                group_row = db.query(ProductGroup.group_key).filter(ProductGroup.id == offer.group_id).first()
                identity_key = group_row[0] if group_row else None
            except Exception:
                pass
        key = item.stable_key or stable_product_key(identity_key=identity_key, product_code=item.product_code, url=item.url, name=item.name)
        block = None
        if item.url:
            block = db.query(DeletedProduct).filter(DeletedProduct.source_url == item.url).first()
        if block is None:
            block = DeletedProduct()
            db.add(block)
        block.source_url = item.url
        block.product_code = item.product_code
        block.identity_key = identity_key
        block.stable_key = key
        block.product_name = item.name
        block.reason = "admin_soft_delete"
        block.deleted_at = now

        item.stable_key = key
        item.is_deleted = True
        item.deleted_at = now
        item.deleted_reason = "admin_delete"
        if offer is not None and hasattr(offer, "is_hidden"):
            offer.is_hidden = True
        record_admin_action(db, action="soft_delete", entity_type="product", entity_id=item.id, details={"name": item.name, "stable_key": key})
        changed += 1
    db.commit()
    return changed


@router.post(
    "/products/{product_id}/delete",
)
def admin_product_delete(product_id: int):
    db = SessionLocal()
    try:
        product = db.query(ProductDB.id).filter(ProductDB.id == product_id).first()
        if product is None:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı.")
        deleted = _delete_product_records(db, [product_id])
        return RedirectResponse(
            url=f"/admin/products?deleted={deleted}",
            status_code=303,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.post(
    "/products/bulk-delete",
)
def admin_products_bulk_delete(product_ids: list[int] = Form(default=[])):
    db = SessionLocal()
    try:
        deleted = _delete_product_records(db, product_ids)
        return RedirectResponse(
            url=f"/admin/products?deleted={deleted}",
            status_code=303,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/products/scan-tasks/{task_id}")
def admin_product_scan_task(task_id: str):
    task = get_cross_store_scan_task(task_id)
    if task is not None:
        return task

    v220 = get_ingestion_task(task_id)
    if v220 is None:
        return JSONResponse(
            {"status": "not_found", "message": "Tarama görevi bulunamadı."},
            status_code=404,
        )

    refresh = v220.get("refresh") or {}
    store_results = refresh.get("store_results") or refresh.get("results") or []
    status_value = str(v220.get("status") or "QUEUED").lower()
    progress = 100 if status_value in ("completed", "failed") else (55 if status_value == "running" else 15)
    return {
        "status": status_value,
        "progress": progress,
        "message": (
            "Ürün kataloğa hazırlandı."
            if status_value == "completed"
            else ("Ürün ekleme başarısız." if status_value == "failed" else "Mağaza teklifleri aranıyor.")
        ),
        "searched_store_count": refresh.get("scanned_store_count", 0),
        "saved_offer_count": refresh.get("newly_saved_offer_count", 0),
        "results": store_results,
        "global_product_id": v220.get("global_product_id"),
        "stage": v220.get("stage"),
        "error": v220.get("error"),
    }


@router.get(
    "/products/add",
    response_class=HTMLResponse,
)
def admin_product_add_form(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="product_add.html",
        context={
            "error": None,
            "success": None,
            "form_data": {},
        },
    )


@router.post(
    "/products/add",
    response_class=HTMLResponse,
)
def admin_product_add(
    request: Request,
    url: str = Form(...),
):
    cleaned_url = url.strip()
    form_data = {
        "url": cleaned_url,
    }

    is_valid, validation_message = validate_product_url(
        cleaned_url
    )

    if not is_valid:
        return templates.TemplateResponse(
            request=request,
            name="product_add.html",
            context={
                "error": validation_message,
                "success": None,
                "form_data": form_data,
            },
            status_code=400,
        )

    try:
        result = start_production_ingestion(url=cleaned_url)
    except Exception as exc:
        return templates.TemplateResponse(
            request=request,
            name="product_add.html",
            context={
                "error": f"{type(exc).__name__}: {exc}",
                "success": None,
                "form_data": form_data,
            },
            status_code=422,
        )

    return templates.TemplateResponse(
        request=request,
        name="product_add.html",
        context={
            "error": None,
            "success": (
                f"Ürün {result.get('store_name') or result.get('store_code')} üzerinden "
                f"kataloğa alındı. Global ürün #{result.get('global_product_id')}; "
                "diğer mağazalar v22 üretim pipeline'ında arka planda aranıyor."
            ),
            "form_data": {},
            "scanned_product": result.get("product"),
            "store_name": result.get("store_name"),
            "cross_store_task_id": result.get("task_id"),
        },
    )


@router.get(
    "/products/{product_id}",
    response_class=HTMLResponse,
)
def admin_product_detail(
    request: Request,
    product_id: int,
):
    db = SessionLocal()

    try:
        product = (
            db.query(ProductDB)
            .filter(
                ProductDB.id == product_id
            )
            .first()
        )

        if product is None:
            raise HTTPException(
                status_code=404,
                detail="ÃœrÃ¼n bulunamadÄ±.",
            )

        price_history = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.product_id
                == product_id
            )
            .order_by(
                PriceHistory.created_at.asc()
            )
            .all()
        )

        discount = calculate_discount(
            current_price=product.price,
            old_price=product.old_price,
        )

        specifications = parse_specifications(
            product.specifications
        )

        chart_labels = [
            history.created_at.strftime(
                "%d.%m.%Y %H:%M"
            )
            for history in price_history
        ]

        chart_prices = [
            round(
                float(history.price),
                2,
            )
            for history in price_history
        ]

        current_price = round(
            float(product.price or 0),
            2,
        )

        if not chart_prices:
            chart_prices = [
                current_price
            ]

            chart_labels = [
                "GÃ¼ncel fiyat"
            ]

        elif chart_prices[-1] != current_price:
            chart_prices.append(
                current_price
            )

            chart_labels.append(
                "GÃ¼ncel fiyat"
            )

        history_prices = [
            float(price)
            for price in chart_prices
        ]

        lowest_price = (
            min(history_prices)
            if history_prices
            else current_price
        )

        highest_price = (
            max(history_prices)
            if history_prices
            else current_price
        )

        average_price = (
            round(
                sum(history_prices)
                / len(history_prices),
                2,
            )
            if history_prices
            else current_price
        )

        ai_reasons = build_ai_reasons(
            product=product,
            discount=discount,
            history_prices=history_prices,
        )

        return templates.TemplateResponse(
            request=request,
            name="product_detail.html",
            context={
                "product": product,
                "discount": discount,
                "specifications": specifications,
                "price_history": price_history,
                "chart_labels": chart_labels,
                "chart_prices": chart_prices,
                "lowest_price": lowest_price,
                "highest_price": highest_price,
                "average_price": average_price,
                "ai_reasons": ai_reasons,
            },
        )

    finally:
        db.close()


# V14_7_0_MODULE_CENTER_BRIDGE
from app.web.admin_module_center_v14_routes import discover_admin_modules


@router.get("/module-center", response_class=HTMLResponse)
def admin_module_center_bridge(request: Request):
    groups = discover_admin_modules(request)
    module_count = sum(len(items) for items in groups.values())
    return templates.TemplateResponse(
        request=request,
        name="admin_module_center_v14.html",
        context={
            "groups": groups,
            "module_count": module_count,
        },
    )

