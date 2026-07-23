from app.notifier.telegram import send_message
from app.database.database import SessionLocal
from app.database.models import ProductDB, PriceHistory
from app.models.product import Product
from app.services.deal_service import is_deal, calculate_discount
from app.ai.scorer import calculate_score


def save_product(product: Product):

    db = SessionLocal()

    try:

        existing = (
            db.query(ProductDB)
            .filter(ProductDB.url == product.url)
            .first()
        )

        if existing:

            old_price = existing.price
            new_price = product.price

            score = calculate_score(product, old_price)

            print("Eski fiyat:", old_price)
            print("Yeni fiyat:", new_price)
            print("Deal mi?:", is_deal(old_price, new_price))
            print(f"🤖 AI SCORE: {score}/100")

            if is_deal(old_price, new_price):

                if existing.last_notified_price == new_price:

                    print(
                        "Bu fiyat için zaten bildirim gönderildi."
                    )

                else:

                    discount = calculate_discount(
                        old_price,
                        new_price
                    )

                    message = f"""
🔥 FIRSAT BULUNDU!

📦 {product.name}

💰 Eski: {old_price:.2f} TL
⚡ Yeni: {new_price:.2f} TL

📉 %{discount} indirim

🤖 AI Skoru: {score}/100

⭐ {product.rating} ({product.review_count} yorum)

🛒 {product.seller}

🔗 {product.url}
"""

                    send_message(message)

                    existing.last_notified_price = new_price

            print("Ürün güncelleniyor...")

            existing.name = product.name
            existing.price = new_price
            existing.old_price = old_price
            existing.rating = product.rating
            existing.review_count = product.review_count
            existing.seller = product.seller
            existing.url = product.url
            existing.image = str(product.image)
            existing.ai_score = score

            if old_price != new_price:

                history = PriceHistory(
                    product_id=existing.id,
                    price=new_price
                )

                db.add(history)

        else:

            print("Yeni ürün ekleniyor...")

            score = calculate_score(
                product,
                product.price
            )

            print(f"🤖 AI SCORE: {score}/100")

            new_product = ProductDB(
                name=product.name,
                price=product.price,
                old_price=product.old_price,
                rating=product.rating,
                review_count=product.review_count,
                seller=product.seller,
                url=product.url,
                image=str(product.image),
                ai_score=score,
                last_notified_price=None
            )

            db.add(new_product)

            db.flush()

            history = PriceHistory(
                product_id=new_product.id,
                price=new_product.price
            )

            db.add(history)

        db.commit()

        print("Veritabanı güncellendi.")

    except Exception as e:

        db.rollback()

        print("Kayıt hatası:", e)

    finally:

        db.close()