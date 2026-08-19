from pathlib import Path

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

marker = "# V14_9_0_DIRECT_MULTI_STORE_ROUTES"
if marker in text:
    print("OK  v14.9.0 doğrudan çok mağazalı route'lar zaten mevcut")
    raise SystemExit(0)

block = '''
# V14_9_0_DIRECT_MULTI_STORE_ROUTES
@app.get("/admin/multi-store-repair", include_in_schema=False)
def direct_multi_store_repair_page(request: Request):
    from app.web.multi_store_offer_repair_v14_routes import templates

    return templates.TemplateResponse(
        request=request,
        name="admin_multi_store_repair_v14.html",
        context={},
    )


@app.post("/api/multi-store-repair/v14/products/{global_product_id}")
def direct_repair_global_product(
    global_product_id: int,
    candidate_limit: int = 5,
    parallel_workers: int = 3,
):
    from fastapi import HTTPException
    from app.services.multi_store_offer_repair_v14_service import (
        product_from_global_product,
        repair_product_across_stores,
    )

    candidate_limit = max(1, min(int(candidate_limit), 10))
    parallel_workers = max(1, min(int(parallel_workers), 6))

    try:
        source = product_from_global_product(global_product_id)
        return repair_product_across_stores(
            source_product=source,
            target_global_product_id=global_product_id,
            candidate_limit=candidate_limit,
            parallel_workers=parallel_workers,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
'''

main_path.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
print("OK  Çok mağazalı admin ve API route'ları doğrudan FastAPI app nesnesine eklendi")
