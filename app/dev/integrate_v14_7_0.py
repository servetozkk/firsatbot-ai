from pathlib import Path

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

import_line = (
    "from app.web.admin_module_center_v14_routes import "
    "router as admin_module_center_v14_router"
)
include_line = "app.include_router(admin_module_center_v14_router)"

if import_line not in text:
    marker = (
        "from app.web.live_price_refresh_v14_routes import "
        "router as live_price_refresh_v14_router"
    )
    if marker in text:
        text = text.replace(marker, marker + "\n" + import_line, 1)
    else:
        text = import_line + "\n" + text

if include_line not in text:
    marker = "app.include_router(live_price_refresh_v14_router)"
    if marker in text:
        text = text.replace(marker, marker + "\n" + include_line, 1)
    else:
        text += "\n" + include_line + "\n"

main_path.write_text(text, encoding="utf-8")
print("OK  Admin Modül Merkezi router entegrasyonu tamamlandı")
