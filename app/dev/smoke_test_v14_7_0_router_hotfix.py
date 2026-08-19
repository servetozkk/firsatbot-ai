from pathlib import Path


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.7.0", "VERSION 14.7.0 korunuyor")

    main_text = (root / "main.py").read_text(encoding="utf-8")
    import_line = (
        "from app.web.admin_module_center_v14_routes import "
        "router as admin_module_center_v14_router"
    )
    include_line = "app.include_router(admin_module_center_v14_router)"

    ok(import_line in main_text, "Modül Merkezi importu mevcut")
    ok(main_text.count(include_line) == 1, "Modül Merkezi include satırı tek ve mevcut")
    ok(
        (root / "app/web/admin_module_center_v14_routes.py").exists(),
        "Modül Merkezi route dosyası mevcut",
    )
    ok(
        (root / "app/templates/admin_module_center_v14.html").exists(),
        "Modül Merkezi template dosyası mevcut",
    )

    print("\nFırsatAI v14.7.0 Modül Merkezi Router hotfix smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
