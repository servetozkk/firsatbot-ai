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
    ok(
        "V14_7_0_DIRECT_MODULE_CENTER_ROUTE" in main_text,
        "doğrudan Modül Merkezi route işareti mevcut",
    )
    ok(
        '@app.get("/admin/module-center"' in main_text,
        "Modül Merkezi doğrudan FastAPI uygulamasına bağlı",
    )
    ok(
        "discover_admin_modules(request)" in main_text,
        "otomatik modül keşfi korunuyor",
    )
    ok(
        (root / "app/web/admin_module_center_v14_routes.py").exists(),
        "modül keşif servisi mevcut",
    )
    ok(
        (root / "app/templates/admin_module_center_v14.html").exists(),
        "Modül Merkezi template dosyası mevcut",
    )

    print("\nFırsatAI v14.7.0 Doğrudan App Modül Merkezi hotfix smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
