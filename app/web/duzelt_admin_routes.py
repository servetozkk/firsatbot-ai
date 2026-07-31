from pathlib import Path


PROJECT_DIR = Path(
    r"C:\Users\Tekno\Downloads\firsatbot-coklu-magaza-guncel-proje"
)

ADMIN_ROUTES_FILE = (
    PROJECT_DIR
    / "app"
    / "web"
    / "admin_routes.py"
)


def main() -> None:
    if not ADMIN_ROUTES_FILE.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {ADMIN_ROUTES_FILE}"
        )

    content = ADMIN_ROUTES_FILE.read_text(
        encoding="utf-8"
    )

    old_fastapi_import = (
        "from fastapi import "
        "APIRouter, HTTPException, Query, Request"
    )

    new_fastapi_import = (
        "from fastapi import "
        "APIRouter, Form, HTTPException, Query, Request"
    )

    old_response_import = (
        "from fastapi.responses import HTMLResponse"
    )

    new_response_import = (
        "from fastapi.responses import "
        "HTMLResponse, RedirectResponse"
    )

    content = content.replace(
        old_fastapi_import,
        new_fastapi_import,
        1,
    )

    content = content.replace(
        old_response_import,
        new_response_import,
        1,
    )

    route_marker = '''@router.get(
    "/products/{product_id}",
    response_class=HTMLResponse,
)
'''

    product_add_routes = '''@router.get(
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
            "form_data": {},
        },
    )


@router.post(
    "/products/add",
)
def admin_product_add(
    request: Request,
    name: str = Form(...),
    url: str = Form(...),
    price: float = Form(...),
    old_price: Optional[float] = Form(
        default=None
    ),
    image_url: Optional[str] = Form(
        default=None
    ),
    seller: Optional[str] = Form(
        default=None
    ),
    category: Optional[str] = Form(
        default=None
    ),
    brand: Optional[str] = Form(
        default=None
    ),
    model: Optional[str] = Form(
        default=None
    ),
    rating: Optional[float] = Form(
        default=None
    ),
    review_count: Optional[int] = Form(
        default=None
    ),
    ai_score: Optional[int] = Form(
        default=None
    ),
    specifications: Optional[str] = Form(
        default=None
    ),
    create_price_history: Optional[str] = Form(
        default=None
    ),
):
    db = SessionLocal()

    cleaned_name = name.strip()
    cleaned_url = url.strip()

    form_data = {
        "name": cleaned_name,
        "url": cleaned_url,
        "price": price,
        "old_price": old_price,
        "image_url": image_url or "",
        "seller": seller or "",
        "category": category or "",
        "brand": brand or "",
        "model": model or "",
        "rating": rating,
        "review_count": review_count,
        "ai_score": ai_score,
        "specifications": specifications or "",
        "create_price_history": (
            create_price_history or ""
        ),
    }

    try:
        if not cleaned_name:
            return templates.TemplateResponse(
                request=request,
                name="product_add.html",
                context={
                    "error": (
                        "Ürün adı boş bırakılamaz."
                    ),
                    "form_data": form_data,
                },
                status_code=400,
            )

        if not cleaned_url:
            return templates.TemplateResponse(
                request=request,
                name="product_add.html",
                context={
                    "error": (
                        "Ürün bağlantısı boş "
                        "bırakılamaz."
                    ),
                    "form_data": form_data,
                },
                status_code=400,
            )

        if price < 0:
            return templates.TemplateResponse(
                request=request,
                name="product_add.html",
                context={
                    "error": (
                        "Ürün fiyatı sıfırdan "
                        "küçük olamaz."
                    ),
                    "form_data": form_data,
                },
                status_code=400,
            )

        if old_price is not None and old_price < 0:
            return templates.TemplateResponse(
                request=request,
                name="product_add.html",
                context={
                    "error": (
                        "Eski fiyat sıfırdan "
                        "küçük olamaz."
                    ),
                    "form_data": form_data,
                },
                status_code=400,
            )

        if rating is not None and not (
            0 <= rating <= 5
        ):
            return templates.TemplateResponse(
                request=request,
                name="product_add.html",
                context={
                    "error": (
                        "Kullanıcı puanı 0 ile 5 "
                        "arasında olmalıdır."
                    ),
                    "form_data": form_data,
                },
                status_code=400,
            )

        if review_count is not None and (
            review_count < 0
        ):
            return templates.TemplateResponse(
                request=request,
                name="product_add.html",
                context={
                    "error": (
                        "Yorum sayısı sıfırdan "
                        "küçük olamaz."
                    ),
                    "form_data": form_data,
                },
                status_code=400,
            )

        if ai_score is not None and not (
            0 <= ai_score <= 100
        ):
            return templates.TemplateResponse(
                request=request,
                name="product_add.html",
                context={
                    "error": (
                        "AI puanı 0 ile 100 "
                        "arasında olmalıdır."
                    ),
                    "form_data": form_data,
                },
                status_code=400,
            )

        existing_product = (
            db.query(ProductDB)
            .filter(
                ProductDB.url == cleaned_url
            )
            .first()
        )

        if existing_product is not None:
            return templates.TemplateResponse(
                request=request,
                name="product_add.html",
                context={
                    "error": (
                        "Bu bağlantıya sahip ürün "
                        "zaten kayıtlı."
                    ),
                    "form_data": form_data,
                },
                status_code=400,
            )
            
            seller=(
                seller.strip()
                if seller
                else None
            ),
            category=(
                category.strip()
                if category
                else None
            ),
            brand=(
                brand.strip()
                if brand
                else None
            ),
            model=(
                model.strip()
                if model
                else None
            ),
            rating=rating,
            review_count=review_count,
            ai_score=ai_score,
            specifications=(
                specifications.strip()
                if specifications
                else None
            ),
        )

        db.add(product)
        db.flush()

        if create_price_history:
            price_history = PriceHistory(
                product_id=product.id,
                price=price,
            )

            db.add(price_history)

        db.commit()
        db.refresh(product)

        return RedirectResponse(
            url=f"/admin/products/{product.id}",
            status_code=303,
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


'''

    if (
        '"/products/add"' not in content
    ):
        if route_marker not in content:
            raise RuntimeError(
                "Ürün detay route'u bulunamadı. "
                "Dosyada beklenmeyen değişiklik var."
            )

        content = content.replace(
            route_marker,
            product_add_routes + route_marker,
            1,
        )

    backup_file = ADMIN_ROUTES_FILE.with_suffix(
        ".py.backup"
    )

    backup_file.write_text(
        ADMIN_ROUTES_FILE.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    ADMIN_ROUTES_FILE.write_text(
        content,
        encoding="utf-8",
    )

    print("İşlem tamamlandı.")
    print(
        f"Düzenlenen dosya: {ADMIN_ROUTES_FILE}"
    )
    print(
        f"Yedek dosya: {backup_file}"
    )


if __name__ == "__main__":
    main()