from pathlib import Path
import ast

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

target_path = "/api/multi-store-repair/v14/products/{global_product_id}"

module = ast.parse(text)
lines = text.splitlines(keepends=True)
remove_ranges = []

for node in module.body:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue

    matched = False
    decorator_start = node.lineno

    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue

        func = decorator.func
        is_post = isinstance(func, ast.Attribute) and func.attr == "post"
        if not is_post or not decorator.args:
            continue

        first_arg = decorator.args[0]
        if isinstance(first_arg, ast.Constant) and first_arg.value == target_path:
            matched = True
            decorator_start = min(
                decorator_start,
                getattr(decorator, "lineno", node.lineno),
            )
            break

    if matched:
        remove_ranges.append(
            (
                decorator_start - 1,
                getattr(node, "end_lineno", node.lineno),
            )
        )

for start, end in sorted(remove_ranges, reverse=True):
    del lines[start:end]

cleaned = "".join(lines).rstrip()

block = '''
# V15_1_2_CANONICAL_MULTI_STORE_API
@app.post("/api/multi-store-repair/v14/products/{global_product_id}")
def canonical_multi_store_repair_v1512(
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
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "GLOBAL_PRODUCT_SOURCE_NOT_FOUND",
                "global_product_id": global_product_id,
                "message": str(error),
            },
        ) from error

    return repair_product_across_stores(
        source_product=source_product,
        target_global_product_id=global_product_id,
        candidate_limit=candidate_limit,
        parallel_workers=parallel_workers,
    )
'''

main_path.write_text(
    cleaned + "\n\n" + block + "\n",
    encoding="utf-8",
)

print(f"OK  Eski çok mağazalı POST route sayısı kaldırıldı: {len(remove_ranges)}")
print("OK  Tek kanonik çok mağazalı POST route eklendi")
