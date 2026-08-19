from pathlib import Path


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.9.0", "VERSION 14.9.0 korunuyor")

    main_text = (root / "main.py").read_text(encoding="utf-8")
    ok(
        "V14_9_0_DIRECT_MULTI_STORE_ROUTES" in main_text,
        "doğrudan route işareti mevcut",
    )
    ok(
        '@app.get("/admin/multi-store-repair"' in main_text,
        "admin çok mağaza sayfası doğrudan app'e bağlı",
    )
    ok(
        '@app.post("/api/multi-store-repair/v14/products/{global_product_id}")'
        in main_text,
        "çok mağazalı birleştirme API doğrudan app'e bağlı",
    )
    ok(
        "repair_product_across_stores" in main_text,
        "çok mağazalı servis endpoint'e bağlı",
    )
    ok(
        (
            root
            / "app/services/multi_store_offer_repair_v14_service.py"
        ).exists(),
        "çok mağazalı birleştirme servisi mevcut",
    )
    ok(
        (
            root
            / "app/templates/admin_multi_store_repair_v14.html"
        ).exists(),
        "çok mağazalı admin template mevcut",
    )

    print(
        "\nFırsatAI v14.9.0 Doğrudan Çok Mağazalı Route "
        "hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
