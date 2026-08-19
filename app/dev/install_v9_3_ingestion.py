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
        anchor = (
            "from app.web.admin_v9_catalog_routes "
            "import router as admin_v9_catalog_router\n"
        )
        if anchor in text:
            text = text.replace(anchor, anchor + import_line, 1)
        else:
            text = import_line + text

    include = "app.include_router(admin_v9_ingestion_router)\n"
    if include not in text:
        anchor = "app.include_router(admin_v9_catalog_router)\n"
        if anchor in text:
            text = text.replace(anchor, anchor + include, 1)
        else:
            pos = text.rfind("app.include_router(")
            end = text.find("\n", pos)
            text = text[:end+1] + include + text[end+1:]
    path.write_text(text, encoding="utf-8")


def patch_scheduler() -> None:
    path = ROOT / "app/scheduler.py"
    text = path.read_text(encoding="utf-8")
    import_line = (
        "from app.services.v9_catalog_ingestion_service "
        "import run_due_catalog_plans\n"
    )
    if import_line not in text:
        lines = text.splitlines(True)
        last_import = 0
        for index, line in enumerate(lines):
            if line.startswith(("import ", "from ")):
                last_import = index + 1
        lines.insert(last_import, import_line)
        text = "".join(lines)

    job_marker = "id='v9_catalog_ingestion'"
    if job_marker not in text:
        addition = """
    scheduler.add_job(
        run_due_catalog_plans,
        trigger="interval",
        minutes=5,
        id='v9_catalog_ingestion',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
"""
        marker = "    scheduler.start()"
        if marker not in text:
            marker = "scheduler.start()"
            addition = addition.replace("\n    ", "\n")
        if marker not in text:
            raise RuntimeError("scheduler.start() bulunamadı.")
        text = text.replace(marker, addition + "\n" + marker, 1)

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
    marker = 'href="/admin/v9-catalog"'
    pos = text.find(marker)
    if pos >= 0:
        end = text.find("</a>", pos)
        text = text[:end+4] + nav + text[end+4:]
    else:
        text += "\n<!-- V9 Katalog Besleme: /admin/v9-ingestion -->\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_main()
    patch_scheduler()
    patch_menu()
    print("V9.3 otomatik katalog besleme entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
