from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.scrapers.trendyol import TrendyolScraper
from app.services.category_service import (
    add_category,
    delete_category,
    get_active_categories,
    get_categories,
    get_category_by_id,
    set_category_active,
)
from app.services.product_config_service import (
    add_product,
)
from app.services.product_service import (
    save_product,
)


router = APIRouter(
    prefix="/api/categories",
    tags=["Kategori Yönetimi"],
)


class CategoryCreateRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    url: str = Field(
        min_length=10,
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=100,
    )

    active: bool = True


class CategoryStatusRequest(BaseModel):
    id: str = Field(
        min_length=1,
    )

    active: bool


class CategoryDeleteRequest(BaseModel):
    id: str = Field(
        min_length=1,
    )


def _get_product_value(
    product: Any,
    field_name: str,
    default: Any = None,
) -> Any:
    """
    Ürün nesnesi sınıf veya sözlük olsa da
    istenen alanı güvenli biçimde alır.
    """

    if isinstance(product, dict):
        return product.get(
            field_name,
            default,
        )

    return getattr(
        product,
        field_name,
        default,
    )


def scan_category_and_save(
    category_url: str,
    limit: int,
) -> dict[str, Any]:
    """
    Trendyol kategorisini tarar.

    Bulunan ürünleri:
    1. Veritabanına kaydeder.
    2. Ürün takip listesine ekler.
    """

    scraper = TrendyolScraper()

    products = scraper.scrape_category(
        category_url=category_url,
        limit=limit,
    )

    if products is None:
        products = []

    found_count = len(products)
    saved_count = 0
    added_to_tracking_count = 0
    already_tracked_count = 0
    failed_count = 0

    errors: list[str] = []

    for product in products:
        product_name = str(
            _get_product_value(
                product,
                "name",
                "",
            )
            or ""
        ).strip()

        product_url = str(
            _get_product_value(
                product,
                "url",
                "",
            )
            or ""
        ).strip()

        if not product_name:
            product_name = "Trendyol Ürünü"

        if not product_url:
            failed_count += 1

            errors.append(
                f"{product_name}: Ürün bağlantısı bulunamadı."
            )

            continue

        try:
            save_product(product)
            saved_count += 1

        except Exception as error:
            failed_count += 1

            errors.append(
                f"{product_name}: Veritabanına kaydedilemedi: {error}"
            )

            continue

        try:
            add_success, add_message = add_product(
                name=product_name,
                url=product_url,
                active=True,
            )

            if add_success:
                added_to_tracking_count += 1

            elif "zaten" in add_message.lower():
                already_tracked_count += 1

            else:
                errors.append(
                    f"{product_name}: {add_message}"
                )

        except Exception as error:
            errors.append(
                f"{product_name}: Takip listesine eklenemedi: {error}"
            )

    return {
        "found_count": found_count,
        "saved_count": saved_count,
        "added_to_tracking_count": (
            added_to_tracking_count
        ),
        "already_tracked_count": (
            already_tracked_count
        ),
        "failed_count": failed_count,
        "errors": errors,
    }


@router.get("")
def list_categories():
    categories = get_categories()

    return {
        "success": True,
        "count": len(categories),
        "categories": categories,
    }


@router.post("")
def create_category(
    data: CategoryCreateRequest,
):
    success, message, category = add_category(
        name=data.name,
        url=data.url,
        limit=data.limit,
        active=data.active,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=message,
        )

    return {
        "success": True,
        "message": message,
        "category": category,
    }


@router.patch("/status")
def update_category_status(
    data: CategoryStatusRequest,
):
    success, message, category = (
        set_category_active(
            category_id=data.id,
            active=data.active,
        )
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=message,
        )

    return {
        "success": True,
        "message": message,
        "category": category,
    }


@router.delete("")
def remove_category(
    data: CategoryDeleteRequest,
):
    success, message = delete_category(
        category_id=data.id,
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

@router.post("/scan-all")
def scan_all_categories():
    categories = get_active_categories()

    if not categories:
        raise HTTPException(
            status_code=400,
            detail="Taranacak aktif kategori bulunamadı.",
        )

    category_results = []

    total_found = 0
    total_saved = 0
    total_added = 0
    total_already_tracked = 0
    total_failed = 0
    failed_category_count = 0

    for category in categories:
        try:
            result = scan_category_and_save(
                category_url=category["url"],
                limit=category["limit"],
            )

            total_found += result["found_count"]
            total_saved += result["saved_count"]
            total_added += result["added_to_tracking_count"]
            total_already_tracked += result[
                "already_tracked_count"
            ]
            total_failed += result["failed_count"]

            category_results.append({
                "category_id": category["id"],
                "category_name": category["name"],
                "success": True,
                **result,
            })

        except Exception as error:
            failed_category_count += 1

            category_results.append({
                "category_id": category["id"],
                "category_name": category["name"],
                "success": False,
                "error": str(error),
            })

            print(
                "Toplu kategori tarama hatası:",
                category.get("name"),
                error,
            )

    successful_category_count = (
        len(categories) - failed_category_count
    )

    message = (
        f"{len(categories)} aktif kategoriden "
        f"{successful_category_count} tanesi tarandı. "
        f"{total_found} ürün bulundu, "
        f"{total_saved} ürün kaydedildi, "
        f"{total_added} yeni ürün takip listesine eklendi."
    )

    if total_already_tracked > 0:
        message += (
            f" {total_already_tracked} ürün "
            "zaten takip listesindeydi."
        )

    if failed_category_count > 0:
        message += (
            f" {failed_category_count} kategori "
            "taranamadı."
        )

    return {
        "success": failed_category_count == 0,
        "message": message,
        "category_count": len(categories),
        "successful_category_count": (
            successful_category_count
        ),
        "failed_category_count": failed_category_count,
        "found_count": total_found,
        "saved_count": total_saved,
        "added_to_tracking_count": total_added,
        "already_tracked_count": total_already_tracked,
        "failed_product_count": total_failed,
        "results": category_results,
    }


@router.post("/{category_id}/scan")
def scan_saved_category(
    category_id: str,
):
    category = get_category_by_id(
        category_id
    )

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Kategori bulunamadı.",
        )

    if not category.get(
        "active",
        False,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Pasif kategori taranamaz. "
                "Önce kategoriyi aktifleştirin."
            ),
        )

    try:
        result = scan_category_and_save(
            category_url=category["url"],
            limit=category["limit"],
        )

    except Exception as error:
        print(
            "Kategori tarama hatası:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Kategori taranırken hata oluştu: "
                f"{error}"
            ),
        ) from error

    message = (
        f'"{category["name"]}" taraması tamamlandı. '
        f'{result["found_count"]} ürün bulundu, '
        f'{result["saved_count"]} ürün kaydedildi, '
        f'{result["added_to_tracking_count"]} ürün '
        "takip listesine eklendi."
    )

    if result["already_tracked_count"] > 0:
        message += (
            f' {result["already_tracked_count"]} ürün '
            "zaten takip listesindeydi."
        )

    if result["failed_count"] > 0:
        message += (
            f' {result["failed_count"]} üründe hata oluştu.'
        )

    return {
        "success": True,
        "message": message,
        "category": category,
        **result,
    }




    category_results = []

    total_found = 0
    total_saved = 0
    total_added = 0
    total_already_tracked = 0
    total_failed = 0
    failed_category_count = 0

    for category in categories:
        try:
            result = scan_category_and_save(
                category_url=category["url"],
                limit=category["limit"],
            )

            total_found += result[
                "found_count"
            ]

            total_saved += result[
                "saved_count"
            ]

            total_added += result[
                "added_to_tracking_count"
            ]

            total_already_tracked += result[
                "already_tracked_count"
            ]

            total_failed += result[
                "failed_count"
            ]

            category_results.append({
                "category_id": category["id"],
                "category_name": category["name"],
                "success": True,
                **result,
            })

        except Exception as error:
            failed_category_count += 1

            category_results.append({
                "category_id": category["id"],
                "category_name": category["name"],
                "success": False,
                "error": str(error),
            })

            print(
                "Toplu kategori tarama hatası:",
                category.get("name"),
                error,
            )

    successful_category_count = (
        len(categories)
        - failed_category_count
    )

    message = (
        f"{len(categories)} aktif kategoriden "
        f"{successful_category_count} tanesi tarandı. "
        f"{total_found} ürün bulundu, "
        f"{total_saved} ürün kaydedildi, "
        f"{total_added} yeni ürün takip listesine eklendi."
    )

    if total_already_tracked > 0:
        message += (
            f" {total_already_tracked} ürün "
            "zaten takip listesindeydi."
        )

    if failed_category_count > 0:
        message += (
            f" {failed_category_count} kategori "
            "taranamadı."
        )

    return {
        "success": failed_category_count == 0,
        "message": message,
        "category_count": len(categories),
        "successful_category_count": (
            successful_category_count
        ),
        "failed_category_count": (
            failed_category_count
        ),
        "found_count": total_found,
        "saved_count": total_saved,
        "added_to_tracking_count": (
            total_added
        ),
        "already_tracked_count": (
            total_already_tracked
        ),
        "failed_product_count": (
            total_failed
        ),
        "results": category_results,
    }