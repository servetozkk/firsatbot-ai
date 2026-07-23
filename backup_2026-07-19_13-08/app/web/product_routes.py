from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.scrapers.trendyol import TrendyolScraper
from app.services.product_service import save_product
from app.services.product_config_service import (
    add_product,
    delete_product,
    get_products,
    set_product_active,
)
from app.database.database import SessionLocal
from app.database.models import ProductDB


router = APIRouter(
    prefix="/api/products",
    tags=["Ürün Yönetimi"],
)


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=10)
    active: bool = True


class ProductStatusRequest(BaseModel):
    url: str = Field(min_length=10)
    active: bool


class ProductUrlRequest(BaseModel):
    url: str = Field(min_length=10)


def scrape_and_save_product(url: str) -> tuple[bool, str]:
    try:
        scraper = TrendyolScraper()
        product = scraper.scrape(url)

        if not product:
            return (
                False,
                "Ürün bilgileri Trendyol'dan alınamadı.",
            )

        save_product(product)

        return (
            True,
            "Ürün başarıyla tarandı ve veritabanına kaydedildi.",
        )

    except Exception as error:
        print("Ürün tarama hatası:", error)

        return (
            False,
            f"Ürün taranırken hata oluştu: {error}",
        )


def get_products_with_details():
    configured_products = get_products()
    db = SessionLocal()

    try:
        database_products = db.query(ProductDB).all()

        products_by_url = {
            product.url: product
            for product in database_products
        }

        result = []

        for configured_product in configured_products:
            product_data = configured_product.copy()

            database_product = products_by_url.get(
                configured_product.get("url")
            )

            if database_product:
                current_price = database_product.price
                old_price = database_product.old_price

                discount_percentage = 0

                if (
                    old_price is not None
                    and current_price is not None
                    and old_price > current_price
                    and old_price > 0
                ):
                    discount_percentage = round(
                        (
                            (old_price - current_price)
                            / old_price
                        )
                        * 100,
                        1,
                    )

                product_data.update({
                    "price": current_price,
                    "old_price": old_price,
                    "discount_percentage": discount_percentage,
                    "rating": database_product.rating,
                    "review_count": database_product.review_count,
                    "seller": database_product.seller,
                    "image": database_product.image,
                    "ai_score": database_product.ai_score,
                    "has_details": True,
                })

            else:
                product_data.update({
                    "price": None,
                    "old_price": None,
                    "discount_percentage": 0,
                    "rating": None,
                    "review_count": None,
                    "seller": None,
                    "image": None,
                    "ai_score": None,
                    "has_details": False,
                })

            result.append(product_data)

        return result

    finally:
        db.close()


@router.get("/stats")
def product_stats():
    products = get_products()

    total_count = len(products)

    active_count = sum(
        1
        for product in products
        if product.get("active", False)
    )

    passive_count = total_count - active_count

    active_percentage = (
        round(
            (active_count / total_count) * 100,
            1,
        )
        if total_count > 0
        else 0
    )

    return {
        "success": True,
        "total_count": total_count,
        "active_count": active_count,
        "passive_count": passive_count,
        "active_percentage": active_percentage,
    }


@router.get("")
def list_products():
    products = get_products_with_details()

    return {
        "success": True,
        "count": len(products),
        "products": products,
    }


@router.post("")
def create_product(data: ProductCreateRequest):
    success, message = add_product(
        name=data.name,
        url=data.url,
        active=data.active,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message,
        )

    scan_success = False
    scan_message = (
        "Ürün pasif eklendiği için tarama yapılmadı."
    )

    if data.active:
        scan_success, scan_message = scrape_and_save_product(
            data.url
        )

    return {
        "success": True,
        "message": message,
        "scan_success": scan_success,
        "scan_message": scan_message,
    }


@router.post("/scan")
def scan_product(data: ProductUrlRequest):
    success, message = scrape_and_save_product(
        data.url
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail=message,
        )

    return {
        "success": True,
        "message": message,
    }


@router.patch("/status")
def update_product_status(
    data: ProductStatusRequest,
):
    success, message = set_product_active(
        url=data.url,
        active=data.active,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=message,
        )

    return {
        "success": True,
        "message": message,
    }


@router.delete("")
def remove_product(data: ProductUrlRequest):
    success, message = delete_product(
        data.url
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=message,
        )

    return {
        "success": True,
        "message": message,
    }