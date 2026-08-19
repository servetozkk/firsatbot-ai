from pathlib import Path

root = Path(__file__).resolve().parents[2]
main = root / "main.py"
text = main.read_text(encoding="utf-8")
import_line = "from app.web.admin_bulk_catalog_routes import router as admin_bulk_catalog_router"
include_line = "app.include_router(admin_bulk_catalog_router)"
if import_line not in text:
    marker = "from fastapi"
    pos = text.find("\n", text.find(marker)) if marker in text else 0
    text = text[:pos+1] + import_line + "\n" + text[pos+1:]
if include_line not in text:
    text += "\n" + include_line + "\n"
main.write_text(text, encoding="utf-8")
print("OK  Toplu katalog router entegrasyonu tamamlandı")
