import json
from datetime import datetime
from typing import Any

from app.ai.scorer import calculate_score
from app.database.database import SessionLocal
from app.database.models import (
    PriceHistory,
    ProductDB,
)
from app.models.product import Product
from app.notifier.telegram import send_product
from app.services.deal_service import calculate_discount
from app.services.multi_store_service import sync_product_offer


MINIMUM_DISCOUNT = 5
MINIMUM_AI_SCORE = 50


def serialize_specifications(
    specifications: Any,
) -> str | None:
    """
    Teknik özellikleri veritabanına kaydedilebilecek
    JSON metnine dönüştürür.
    """

    if specifications is None:
        return None

    if isinstance(specifications, str):
        return specifications

    try:
        return json.dumps(
            specifications,
            ensure_ascii=False,
        )

    except (TypeError, ValueError):
        return str(specifications)


def update_optional_field(
    database_product: ProductDB,
    field_name: str,
    value: Any,
) -> None:
    """
    Yeni değer boş değilse ürün alanını günceller.

    Scraper bazı alanları göndermediğinde daha önce
    kaydedilmiş değerlerin silinmesini engeller.
    """

    if value is not None and value != "":
        setattr(
            database_product,
            field_name,
            value,
        )


def should_send_notification(
    *,
    price_dropped: bool,
    minimum_discount_reached: bool,
    minimum_score_reached: bool,
    better_than_last_notification: bool,
) -> bool:
    """
    Ürün için Telegram bildirimi gönderilip
    gönderilmeyeceğini belirler.
    """

    return all(
        (
            price_dropped,
            minimum_discount_reached,
            minimum_score_reached,
            better_than_last_notification,
        )
    )


def print_notification_skip_reason(
    *,
    price_changed: bool,
    price_dropped: bool,
    discount: float,
    score: int,
    better_than_last_notification: bool,
) -> None:
    """
    Bildirim gönderilmeme nedenini terminale yazdırır.
    """

    if not price_changed:
        print(
            "Fiyat değişmedi, bildirim gönderilmedi."
        )

    elif not price_dropped:
        print(
            "Fiyat yükseldi, bildirim gönderilmedi."
        )

    elif discount < MINIMUM_DISCOUNT:
        print(
            f"İndirim %{discount}. "
            f"Minimum %{MINIMUM_DISCOUNT} olmadığı için "
            "bildirim gönderilmedi."
        )

    elif score < MINIMUM_AI_SCORE:
        print(
            f"AI skoru {score}. "
            f"Minimum {MINIMUM_AI_SCORE} olmadığı için "
            "bildirim gönderilmedi."
        )

    elif not better_than_last_notification:
        print(
            "Bu fiyat daha önce bildirilen fiyattan "
            "daha iyi değil."
        )


def send_price_drop_notification(
    *,
    product: Product,
    database_product: ProductDB,
    old_price: float,
    new_price: float,
    discount: float,
    score: int,
) -> bool:
    """
    Telegram fiyat düşüşü bildirimi gönderir.

    Gönderim başarılı olursa son bildirilen fiyatı
    günceller.
    """

    telegram_sent = send_product(
        product_name=product.name,
        old_price=old_price,
        new_price=new_price,
        price_drop_percent=discount,
        ai_score=score,
        opportunity_score=score,
        seller=product.seller,
        rating=product.rating,
        review_count=product.review_count,
        product_url=product.url,
        image_url=product.image,
    )

    if telegram_sent:
        database_product.last_notified_price = new_price

        print(
            "Telegram bildirimi gönderildi."
        )

        return True

    print(
        "Telegram bildirimi gönderilemedi. "
        "Son bildirilen fiyat güncellenmedi."
    )

    return False


def update_existing_product(
    *,
    db,
    existing: ProductDB,
    product: Product,
    now: datetime,
) -> None:
    """
    Mevcut ürünü, fiyat geçmişini ve çoklu mağaza
    teklif kaydını günceller.
    """

    old_price = float(existing.price)
    new_price = float(product.price)

    score = calculate_score(
        product,
        old_price,
    )

    discount = calculate_discount(
        old_price,
        new_price,
    )

    price_changed = (
        abs(old_price - new_price) >= 0.01
    )

    price_dropped = (
        price_changed
        and new_price < old_price
    )

    minimum_discount_reached = (
        discount >= MINIMUM_DISCOUNT
    )

    minimum_score_reached = (
        score >= MINIMUM_AI_SCORE
    )

    better_than_last_notification = (
        existing.last_notified_price is None
        or new_price
        < float(existing.last_notified_price)
    )

    print("Eski fiyat:", old_price)
    print("Yeni fiyat:", new_price)
    print(f"İndirim: %{discount}")
    print(f"AI SCORE: {score}/100")

    notification_required = (
        should_send_notification(
            price_dropped=price_dropped,
            minimum_discount_reached=(
                minimum_discount_reached
            ),
            minimum_score_reached=(
                minimum_score_reached
            ),
            better_than_last_notification=(
                better_than_last_notification
            ),
        )
    )

    if notification_required:
        send_price_drop_notification(
            product=product,
            database_product=existing,
            old_price=old_price,
            new_price=new_price,
            discount=discount,
            score=score,
        )

    else:
        print_notification_skip_reason(
            price_changed=price_changed,
            price_dropped=price_dropped,
            discount=discount,
            score=score,
            better_than_last_notification=(
                better_than_last_notification
            ),
        )

    print("Ürün güncelleniyor...")

    existing.name = product.name
    existing.price = new_price
    existing.old_price = old_price
    existing.rating = product.rating
    existing.review_count = product.review_count
    existing.seller = product.seller
    existing.url = product.url
    existing.ai_score = score
    existing.updated_at = now

    if product.image:
        existing.image = str(product.image)

    update_optional_field(
        existing,
        "brand",
        product.brand,
    )

    update_optional_field(
        existing,
        "model",
        product.model,
    )

    update_optional_field(
        existing,
        "category",
        product.category,
    )

    update_optional_field(
        existing,
        "description",
        product.description,
    )

    update_optional_field(
        existing,
        "stock_status",
        product.stock_status,
    )

    update_optional_field(
        existing,
        "source_site",
        product.source_site,
    )

    update_optional_field(
        existing,
        "product_code",
        product.product_code,
    )

    serialized_specifications = (
        serialize_specifications(
            product.specifications
        )
    )

    update_optional_field(
        existing,
        "specifications",
        serialized_specifications,
    )

    if price_changed:
        existing.last_price_change = now

        history = PriceHistory(
            product_id=existing.id,
            price=new_price,
            created_at=now,
        )

        db.add(history)

        print(
            "Yeni fiyat geçmişe kaydedildi."
        )

    sync_product_offer(
        db=db,
        database_product=existing,
        product=product,
        price_changed=price_changed,
    )


def create_new_product(
    *,
    db,
    product: Product,
    now: datetime,
) -> ProductDB:
    """
    Yeni ürünü, ilk fiyat geçmişini ve ilk mağaza
    teklifini oluşturur.
    """

    print("Yeni ürün ekleniyor...")

    new_price = float(product.price)

    score = calculate_score(
        product,
        new_price,
    )

    print(f"AI SCORE: {score}/100")

    new_product = ProductDB(
        name=product.name,
        price=new_price,
        old_price=product.old_price,
        rating=product.rating,
        review_count=product.review_count,
        seller=product.seller,
        url=product.url,
        image=(
            str(product.image)
            if product.image
            else None
        ),
        ai_score=score,
        last_notified_price=None,
        brand=product.brand,
        model=product.model,
        category=product.category,
        description=product.description,
        specifications=serialize_specifications(
            product.specifications
        ),
        stock_status=(
            product.stock_status
            or "Bilinmiyor"
        ),
        source_site=product.source_site,
        product_code=product.product_code,
        last_price_change=now,
        created_at=now,
        updated_at=now,
    )

    db.add(new_product)
    db.flush()

    history = PriceHistory(
        product_id=new_product.id,
        price=new_price,
        created_at=now,
    )

    db.add(history)

    sync_product_offer(
        db=db,
        database_product=new_product,
        product=product,
        price_changed=True,
    )

    print(
        "Yeni ürün, mağaza teklifi ve "
        "ilk fiyat geçmişi kaydedildi."
    )

    return new_product


def save_product(
    product: Product,
) -> None:
    """
    Scraper tarafından gelen ürünü veritabanına kaydeder.

    Mevcut ürünleri günceller, fiyat geçmişini saklar,
    çoklu mağaza tekliflerini senkronize eder ve gerekli
    durumlarda Telegram bildirimi gönderir.
    """

    db = SessionLocal()

    try:
        existing = (
            db.query(ProductDB)
            .filter(
                ProductDB.url == product.url
            )
            .first()
        )

        now = datetime.utcnow()

        if existing:
            update_existing_product(
                db=db,
                existing=existing,
                product=product,
                now=now,
            )

        else:
            create_new_product(
                db=db,
                product=product,
                now=now,
            )

        db.commit()

        print(
            "Veritabanı güncellendi."
        )

    except Exception as error:
        db.rollback()

        print(
            "Kayıt hatası:",
            error,
        )

        raise

    finally:
        db.close()