from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "main.py"
source = MAIN.read_text(encoding="utf-8")
import_line = "from app.web.scraper_operations_routes import router as scraper_operations_router"
include_line = "app.include_router(scraper_operations_router)"

if import_line not in source:
    marker = "# Routerlar"
    if marker in source:
        source = source.replace(marker, import_line + "\n\n" + marker, 1)
    else:
        source += "\n" + import_line + "\n"

if include_line not in source:
    marker = "app.include_router(api_cache_router)"
    if marker in source:
        source = source.replace(marker, include_line + "\n" + marker, 1)
    else:
        source += "\n" + include_line + "\n"

MAIN.write_text(source, encoding="utf-8")
print("OK  Scraper operasyon router entegrasyonu tamamlandı")
