from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.category_discovery_service import CategoryDiscoveryService
from app.services.category_service import (
    add_category,
    delete_category,
    get_active_categories,
    get_categories,
    get_category_by_id,
    set_category_active,
)


router = APIRouter(
    prefix="/api/categories",
    tags=["Kategori Yönetimi"],
)

_discovery_service = CategoryDiscoveryService()


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=10)
    limit: int = Field(default=100, ge=1, le=5000)
    active: bool = True


class CategoryStatusRequest(BaseModel):
    id: str = Field(min_length=1)
    active: bool


class CategoryDeleteRequest(BaseModel):
    id: str = Field(min_length=1)


def scan_category_and_save(
    category_url: str,
    limit: int,
    max_pages: int = 10,
) -> dict:
    return _discovery_service.scan_and_save(
        category_url=category_url,
        limit=limit,
        max_pages=max_pages,
    ).to_dict()


@router.get("")
def list_categories():
    categories = get_categories()
    return {
        "success": True,
        "count": len(categories),
        "categories": categories,
    }


@router.post("")
def create_category(data: CategoryCreateRequest):
    success, message, category = add_category(
        name=data.name,
        url=data.url,
        limit=data.limit,
        active=data.active,
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {
        "success": True,
        "message": message,
        "category": category,
    }


@router.patch("/status")
def update_category_status(data: CategoryStatusRequest):
    success, message, category = set_category_active(
        category_id=data.id,
        active=data.active,
    )
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {
        "success": True,
        "message": message,
        "category": category,
    }


@router.delete("")
def remove_category(data: CategoryDeleteRequest):
    success, message = delete_category(category_id=data.id)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    return {"success": True, "message": message}


@router.post("/scan-all")
def scan_all_categories():
    categories = get_active_categories()
    if not categories:
        raise HTTPException(
            status_code=400,
            detail="Taranacak aktif kategori bulunamadı.",
        )

    category_results = []
    totals = {
        "found_count": 0,
        "saved_count": 0,
        "added_to_tracking_count": 0,
        "already_tracked_count": 0,
        "failed_count": 0,
    }
    failed_category_count = 0

    for category in categories:
        try:
            result = scan_category_and_save(
                category_url=category["url"],
                limit=category["limit"],
            )
            for key in totals:
                totals[key] += int(result.get(key, 0))
            category_results.append({
                "category_id": category["id"],
                "category_name": category["name"],
                **result,
            })
            if not result.get("success", False):
                failed_category_count += 1
        except Exception as error:
            failed_category_count += 1
            category_results.append({
                "category_id": category["id"],
                "category_name": category["name"],
                "success": False,
                "error": f"{type(error).__name__}: {error}",
            })

    successful_category_count = len(categories) - failed_category_count
    return {
        "success": failed_category_count == 0,
        "message": (
            f"{len(categories)} aktif kategoriden "
            f"{successful_category_count} tanesi tarandı. "
            f"{totals['found_count']} ürün bulundu, "
            f"{totals['saved_count']} ürün kaydedildi."
        ),
        "category_count": len(categories),
        "successful_category_count": successful_category_count,
        "failed_category_count": failed_category_count,
        **totals,
        "results": category_results,
    }


@router.post("/{category_id}/scan")
def scan_single_category(category_id: str):
    category = get_category_by_id(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı.")

    try:
        result = scan_category_and_save(
            category_url=category["url"],
            limit=category["limit"],
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"{type(error).__name__}: {error}",
        ) from error

    return {
        "success": result.get("success", False),
        "message": (
            f"{result.get('store_name', 'Mağaza')} kategorisinde "
            f"{result.get('found_count', 0)} ürün bulundu, "
            f"{result.get('saved_count', 0)} ürün kaydedildi."
        ),
        "category": category,
        **result,
    }
