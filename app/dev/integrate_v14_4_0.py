from pathlib import Path

root = Path.cwd()
main = root / "main.py"
text = main.read_text(encoding="utf-8")
import_line = "from app.web.global_marketplace_v14_routes import router as global_marketplace_v14_router"
include_line = "app.include_router(global_marketplace_v14_router)"
if import_line not in text:
    marker = "# Routerlar"
    text = text.replace(marker, import_line + "\n\n" + marker, 1)
if include_line not in text:
    marker = "app.include_router(scraper_operations_router)"
    text = text.replace(marker, include_line + "\n" + marker, 1)
main.write_text(text, encoding="utf-8")
print("OK  Global marketplace router entegrasyonu tamamlandı")
