from pathlib import Path


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.7.0", "VERSION 14.7.0 korunuyor")

    admin_text = (
        root / "app/web/admin_routes.py"
    ).read_text(encoding="utf-8")
    ok(
        "V14_7_0_MODULE_CENTER_BRIDGE" in admin_text,
        "Modül Merkezi admin köprüsü mevcut",
    )
    ok(
        '@router.get("/module-center"' in admin_text,
        "Modül Merkezi ana admin router altında tanımlı",
    )
    ok(
        "discover_admin_modules" in admin_text,
        "otomatik modül keşfi korunuyor",
    )
    ok(
        (root / "app/templates/admin_module_center_v14.html").exists(),
        "Modül Merkezi template dosyası mevcut",
    )

    print("\nFırsatAI v14.7.0 Admin Router Köprü hotfix smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
