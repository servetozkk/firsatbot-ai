from pathlib import Path

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

marker = "# V14_9_2_DIRECT_GLOBAL_MARKETPLACE_ROUTE"
if marker in text:
    print("OK  v14.9.2 doğrudan global marketplace route zaten mevcut")
    raise SystemExit(0)

block = r'''
# V14_9_2_DIRECT_GLOBAL_MARKETPLACE_ROUTE
@app.middleware("http")
async def legacy_global_product_slug_redirect(request, call_next):
    import re
    from fastapi.responses import RedirectResponse

    path = request.url.path
    match = re.fullmatch(r"/fiyat-karsilastirma/(\\d+)-(.+)", path)
    if match:
        return RedirectResponse(
            url=f"/fiyat-karsilastirma/global/{match.group(1)}-{match.group(2)}",
            status_code=301,
        )

    return await call_next(request)


@app.get(
    "/fiyat-karsilastirma/global/{product_ref}",
    include_in_schema=False,
)
def direct_global_marketplace_product(request: Request, product_ref: str):
    import re
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse
    from fastapi.templating import Jinja2Templates

    from app.services.ai_comparison_v14_service import analyze_global_product
    from app.services.global_price_experience_v14_service import get_price_history
    from app.services.global_marketplace_v14_service import get_global_product

    match = re.match(r"^\s*(\d+)(?:-|$)", str(product_ref or ""))
    if not match:
        raise HTTPException(
            status_code=404,
            detail="Ürün adresinden geçerli global ürün kimliği çıkarılamadı",
        )

    product_id = int(match.group(1))
    product = get_global_product(product_id)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Global ürün veya aktif teklif bulunamadı",
        )

    canonical_path = (
        f"/fiyat-karsilastirma/global/{product_id}-{product['slug']}"
    )
    if request.url.path != canonical_path:
        return RedirectResponse(url=canonical_path, status_code=301)

    product["ai_insight"] = analyze_global_product(product_id)
    product["price_history"] = get_price_history(product_id, days=90)

    local_templates = Jinja2Templates(
        directory=str(Path(__file__).resolve().parent / "app" / "templates")
    )

    return local_templates.TemplateResponse(
        request=request,
        name="global_marketplace_product_v14.html",
        context={
            "product": product,
            "seo_title": (
                f"{product['canonical_name']} Fiyatları "
                "ve Mağaza Karşılaştırması"
            ),
            "seo_description": (
                f"{product['canonical_name']} için "
                f"{product['store_count']} mağazadaki fiyatları karşılaştırın."
            ),
            "canonical_url": (
                str(request.base_url).rstrip("/") + canonical_path
            ),
        },
    )
'''

main_path.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
print("OK  Global ürün SEO route ve eski URL yönlendirmesi doğrudan FastAPI app'e eklendi")
