import json
from datetime import datetime
from typing import Any

from app.notifier.telegram import send_product
from app.database.database import SessionLocal
from app.database.models import ProductDB, PriceHistory
from app.models.product import Product
from app.services.deal_service import calculate_discount
from app.ai.scorer import calculate_score


MINIMUM_DISCOUNT = 5
MINIMUM_AI_SCORE = 50


def serialize_specifications(
    specifications: Any,
) -> str | None:
    """
    Teknik özellikleri veritabanına JSON metni
    şeklinde kaydeder.
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
    Yeni veri boş değilse mevcut alanı günceller.

    Scraper yeni detay göndermediğinde daha önce
    kaydedilmiş marka, model veya teknik özelliklerin
    silinmesini engeller.
    """

    if value is not None and value != "":
        setattr(
            database_product,
            field_name,
            value,
        )


def save_product(product: Product) -> None:
    db = SessionLocal()

    try:
        existing = (
            db.query(ProductDB)
            .filter(ProductDB.url == product.url)
            .first()
        )

        now = datetime.utcnow()

        if existing:
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

            if (
                price_dropped
                and minimum_discount_reached
                and minimum_score_reached
                and better_than_last_notification
            ):
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
                    existing.last_notified_price = new_price

                    print(
                        "Telegram bildirimi gönderildi."
                    )

                else:
                    print(
                        "Telegram bildirimi gönderilemedi. "
                        "Son bildirilen fiyat güncellenmedi."
                    )

            elif not price_changed:
                print(
                    "Fiyat değişmedi, bildirim gönderilmedi."
                )

            elif not price_dropped:
                print(
                    "Fiyat yükseldi, bildirim gönderilmedi."
                )

            elif not minimum_discount_reached:
                print(
                    f"İndirim %{discount}. "
                    f"Minimum %{MINIMUM_DISCOUNT} olmadığı için "
                    "bildirim gönderilmedi."
                )

            elif not minimum_score_reached:
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

            print("Ürün güncelleniyor...")

            existing.name = product.name
            existing.price = new_price
            existing.old_price = old_price
            existing.rating = product.rating
            existing.review_count = product.review_count
            existing.seller = product.seller
            existing.url = product.url

            existing.image = (
                str(product.image)
                if product.image
                else existing.image
            )

            existing.ai_score = score
            existing.updated_at = now

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
                )

                db.add(history)

                print(
                    "Yeni fiyat geçmişe kaydedildi."
                )

        else:
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
            )

            db.add(history)

            print(
                "Yeni ürün ve ilk fiyat geçmişi kaydedildi."
            )

        db.commit()

        print("Veritabanı güncellendi.")

    except Exception as error:
        db.rollback()

        print(
            "Kayıt hatası:",
            error,
        )

        raise

    finally:
        db.close()