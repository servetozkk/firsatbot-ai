from pathlib import Path
import ast

r = Path(__file__).resolve().parents[2]
repair = (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
cross = (r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
main = (r/"main.py").read_text(encoding="utf-8")

ast.parse(repair)
ast.parse(cross)
ast.parse(main)

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip() == "23.62.4"),
    ("binding source color extraction", "source_color_v23624 = self._source_color_from_text_v23623" in repair),
    ("binding source color log", "V23.62.4 BINDING SOURCE COLOR" in repair),
    ("binding passes source product", "source_product=source_product" in repair),
    ("binding passes explicit color", "source_color_v23623=source_color_v23624" in repair),
    ("base color parser preserved", "def _source_color_from_text_v23623" in cross),
    ("card color priority preserved", "v23622_color_priority" in cross),
    ("detail order observability preserved", "CARD-COLOR DETAIL ORDER" in cross),
    ("variant gate preserved", "validate_variant(" in cross),
    ("same-product gate preserved", "self._is_same_product(" in cross),
    ("runtime", "/api/runtime-identity/v23624" in main),
    ("v23623 preserved", "/api/runtime-identity/v23623" in main),
]

for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)

raise SystemExit(0 if all(ok for _, ok in checks) else 1)
