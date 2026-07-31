from fastapi import APIRouter

from app.services.category_service import get_categories
from app.services.product_config_service import get_products

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


@router.get("")
def dashboard():
    categories = get_categories()
    products = get_products()

    active_categories = [
        category
        for category in categories
        if category.get("active", False)
    ]

    active_products = [
        product
        for product in products
        if product.get("active", False)
    ]

    return {
        "success": True,
        "category_count": len(categories),
        "active_category_count": len(active_categories),
        "tracked_product_count": len(products),
        "active_product_count": len(active_products),
    }
