from pathlib import Path

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

import_line = (
    "from app.web.ai_comparison_v14_routes import "
    "router as ai_comparison_v14_router"
)
include_line = "app.include_router(ai_comparison_v14_router)"

if import_line not in text:
    marker = (
        "from app.web.global_marketplace_v14_routes import "
        "router as global_marketplace_v14_router"
    )
    text = text.replace(marker, marker + "\n" + import_line, 1)

if include_line not in text:
    marker = "app.include_router(global_marketplace_v14_router)"
    text = text.replace(marker, marker + "\n" + include_line, 1)

main_path.write_text(text, encoding="utf-8")
print("OK  AI karşılaştırma router entegrasyonu tamamlandı")
