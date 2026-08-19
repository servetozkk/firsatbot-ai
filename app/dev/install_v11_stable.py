from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()


def patch_config() -> None:
    path = ROOT / "app/core/config.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        'app_version: str = os.getenv("APP_VERSION", "8.0.0")',
        'app_version: str = os.getenv("APP_VERSION", "11.0.0")',
        1,
    )
    path.write_text(text, encoding="utf-8")


def patch_main() -> None:
    path = ROOT / "main.py"
    text = path.read_text(encoding="utf-8-sig")
    import_line = (
        "from app.web.admin_v11_stable_routes "
        "import router as admin_v11_stable_router\n"
    )
    if import_line not in text:
        anchor = (
            "from app.web.admin_v10_security_routes "
            "import router as admin_v10_security_router\n"
        )
        if anchor in text:
            text = text.replace(anchor, anchor + import_line, 1)
        else:
            text = import_line + text

    include = "app.include_router(admin_v11_stable_router)\n"
    if include not in text:
        anchor = "app.include_router(admin_v10_security_router)\n"
        if anchor in text:
            text = text.replace(anchor, anchor + include, 1)
        else:
            position = text.rfind("app.include_router(")
            line_end = text.find("\n", position)
            text = text[:line_end + 1] + include + text[line_end + 1:]
    path.write_text(text, encoding="utf-8-sig")


def patch_menu() -> None:
    path = ROOT / "app/templates/base.html"
    text = path.read_text(encoding="utf-8")
    if "/admin/v11-stable" not in text:
        text += (
            '\n<a style="display:none" href="/admin/v11-stable">'
            'FırsatAI 11.0 Stable</a>\n'
        )
    path.write_text(text, encoding="utf-8")


def write_version() -> None:
    (ROOT / "VERSION").write_text("11.0.0\n", encoding="utf-8")


def main() -> int:
    patch_config()
    patch_main()
    patch_menu()
    write_version()
    print("FırsatAI 11.0 Stable entegrasyonu tamamlandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
