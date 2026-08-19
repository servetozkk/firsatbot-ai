from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()


def patch_main() -> None:
    path = ROOT / "main.py"
    text = path.read_text(encoding="utf-8")

    import_line = (
        "from app.web.admin_v9_ingestion_routes "
        "import router as admin_v9_ingestion_router\n"
    )
    if import_line not in text:
        anchors = [
            (
                "from app.web.admin_v9_catalog_routes "
                "import router as admin_v9_catalog_router\n"
            ),
            (
                "from app.web.admin_catalog_scan_routes "
                "import router as admin_catalog_scan_router\n"
            ),
        ]
        inserted = False
        for anchor in anchors:
            if anchor in text:
                text = text.replace(anchor, anchor + import_line, 1)
                inserted = True
                break
        if not inserted:
            text = import_line + text

    include = "app.include_router(admin_v9_ingestion_router)\n"
    if include not in text:
        anchors = [
            "app.include_router(admin_v9_catalog_router)\n",
            "app.include_router(admin_catalog_scan_router)\n",
        ]
        inserted = False
        for anchor in anchors:
            if anchor in text:
                text = text.replace(anchor, anchor + include, 1)
                inserted = True
                break
        if not inserted:
            position = text.rfind("app.include_router(")
            if position < 0:
                raise RuntimeError("main.py router ekleme noktası bulunamadı.")
            line_end = text.find("\n", position)
            text = text[:line_end + 1] + include + text[line_end + 1:]

    path.write_text(text, encoding="utf-8")


def patch_menu() -> None:
    path = ROOT / "app/templates/base.html"
    text = path.read_text(encoding="utf-8")

    if "/admin/v9-ingestion" in text:
        return

    nav = (
        '\n            <a class="admin-nav-item '
        '{% if request.url.path == \'/admin/v9-ingestion\' %}active{% endif %}" '
        'href="/admin/v9-ingestion"><span>V9</span> Katalog Besleme</a>'
    )

    for marker in ('href="/admin/v9-catalog"', 'href="/admin/catalog-scans"'):
        position = text.find(marker)
        if position >= 0:
            end = text.find("</a>", position)
            if end >= 0:
                text = text[:end + 4] + nav + text[end + 4:]
                path.write_text(text, encoding="utf-8")
                return

    text += "\n<!-- V9 Katalog Besleme: /admin/v9-ingestion -->\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_main()
    patch_menu()
    print(
        "V9.3.1 entegrasyonu tamamlandı. "
        "Mevcut scheduler.py dosyası değiştirilmedi."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
