from __future__ import annotations

import ast
import re
from pathlib import Path


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    ok((root / "VERSION").read_text(encoding="utf-8").strip() == "18.0.0", "VERSION 18.0.0")
    path = root / "app/services/cross_store_search_service.py"
    source = path.read_text(encoding="utf-8")
    ok("V18_0_SEARCH_RESULT_PREFILTER" in source, "V18 ön eleme motoru mevcut")
    ok("strong[:3]" in source, "detay taraması en fazla üç güçlü aday")
    tree = ast.parse(source)
    wanted = {"_fold_search_text", "_query_identity_tokens", "_search_result_candidate_score"}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    namespace = {"re": re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<v18>", "exec"), namespace)
    score = namespace["_search_result_candidate_score"]
    query = "ASUS vivobook 15 x1504va-bq5391 intel core 5 120u 8gb ram 512gb ssd"
    exact, _ = score(search_query=query, href="https://x/asus-x1504va-bq5391-p-1", label="ASUS Vivobook X1504VA-BQ5391 Core 5 120U 8GB 512GB")
    conflict, _ = score(search_query=query, href="https://x/asus-x1504va-bq5383w-p-1", label="ASUS Vivobook X1504VA-BQ5383W Core 5 120U 8GB 512GB")
    family, _ = score(search_query=query, href="https://x/asus-x1504va-p-1", label="ASUS Vivobook X1504VA Core 5 120U 8GB 512GB")
    wrong, _ = score(search_query=query, href="https://x/asus-tuf-p-1", label="ASUS TUF Gaming A16 RTX5060")
    ok(exact >= 100, "tam BQ5391 öncelikli")
    ok(conflict < 0, "BQ5383W detay açılmadan reddediliyor")
    ok(family >= 70, "son eki eksik X1504VA kontrollü kabul")
    ok(wrong < 0, "TUF/model ailesi farklı aday reddediliyor")
    ok('/api/runtime-identity/v18' in (root/'main.py').read_text(encoding='utf-8'), "runtime v18 endpoint mevcut")
    print("\nFırsatAI v18.0.0 aday ön eleme smoke testi başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
