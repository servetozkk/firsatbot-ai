from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
tree = ast.parse(source)
needed = {
    "_fold_search_text", "_extract_search_hardware", "_query_identity_tokens",
    "_explicit_candidate_family", "_product_type_gate_reason",
    "_candidate_variant_after_family", "_search_result_candidate_score",
}
body = []
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "ACCESSORY_STRONG_TOKENS"
        for target in node.targets
    ):
        body.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name in needed:
        body.append(node)
namespace = {"re": re}
exec(compile(ast.Module(body=body, type_ignores=[]), "v216_quality_subset", "exec"), namespace)
score = namespace["_search_result_candidate_score"]
query = "ASUS x1504va bq5391 8GB RAM 512GB SSD 120u"

assert score(
    search_query=query,
    href="https://www.n11.com/urun/yeni-nesil-pinli-uc-model-65w-asus-vivobook-15-x1504za-bq451-uyumlu-notebook-adaptor-111122344",
    label="ASUS Vivobook 15 X1504ZA-BQ451 uyumlu notebook adaptor",
)[0] == -980
assert score(
    search_query=query,
    href="https://shop.test/asus-vivobook-15-x1504za-bq5391-8gb-512gb",
    label="ASUS Vivobook 15 X1504ZA-BQ5391 8GB RAM 512GB SSD Core 5 120U",
)[0] == -970
assert score(
    search_query=query,
    href="https://shop.test/asus-vivobook-15-x1504va-bq3970w",
    label="ASUS Vivobook 15 X1504VA-BQ3970W 8GB RAM 512GB SSD Core 5 120U",
)[0] == -950
assert score(
    search_query=query,
    href="https://shop.test/asus-vivobook-15-x1504va-bq5391",
    label="ASUS Vivobook 15 X1504VA-BQ5391 8GB RAM 512GB SSD Core 5 120U",
)[0] >= 300

assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "21.6.0"
assert "/api/runtime-identity/v216" in (ROOT / "main.py").read_text(encoding="utf-8")
print("OK v21.6 product type + family + variant discovery quality gates")
