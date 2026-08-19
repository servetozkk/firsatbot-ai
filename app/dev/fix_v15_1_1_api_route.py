from pathlib import Path

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

marker = "# V15_1_1_DIRECT_MULTI_STORE_API"

if marker in text:
    print("OK  v15.1.1 doğrudan çok mağazalı API route zaten mevcut")
    raise SystemExit(0)

block = '''
# V15_1_1_DIRECT_MULTI_STORE_API
@app.post("/api/multi-store-repair/v14/products/{global_product_id}")
def direct_multi_store_repair_v1511(
    global_product_id: int,
    candidate_limit: int = 50,
    parallel_workers: int = 3,
):
    from fastapi import HTTPException
    from app.services.multi_store_offer_repair_v14_service import (
        product_from_global_product,
        repair_product_across_stores,
    )

    candidate_limit = max(10, min(int(candidate_limit), 50))
    parallel_workers = max(1, min(int(parallel_workers), 6))

    try:
        source_product = product_from_global_product(global_product_id)
        return repair_product_across_stores(
            source_product=source_product,
            target_global_product_id=global_product_id,
            candidate_limit=candidate_limit,
            parallel_workers=parallel_workers,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
'''

main_path.write_text(
    text.rstrip() + "\n\n" + block + "\n",
    encoding="utf-8",
)

print("OK  Çok mağazalı API route doğrudan FastAPI app nesnesine eklendi")
