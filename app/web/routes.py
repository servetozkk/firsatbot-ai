from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.database.models import ProductDB, PriceHistory


router = APIRouter()

templates = Jinja2Templates(
    directory="app/web/templates"
)


@router.get("/")
def home(request: Request):

    db = SessionLocal()

    try:
        products = db.query(ProductDB).all()

        total_products = len(products)

        average_price = (
            round(
                sum(product.price for product in products)
                / total_products,
                2
            )
            if total_products
            else 0
        )

        highest_price = max(
            (product.price for product in products),
            default=0
        )

        lowest_price = min(
            (product.price for product in products),
            default=0
        )

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "products": products,
                "total_products": total_products,
                "average_price": average_price,
                "highest_price": highest_price,
                "lowest_price": lowest_price,
            }
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
                        "%d.%m.%Y %H:%M"
                    )
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