from pathlib import Path


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.9.2", "VERSION 14.9.2")

    main_text = (root / "main.py").read_text(encoding="utf-8")

    ok(
        "V14_9_2_DIRECT_GLOBAL_MARKETPLACE_ROUTE" in main_text,
        "doğrudan global marketplace route işareti mevcut",
    )
    ok(
        '@app.middleware("http")' in main_text,
        "eski SEO URL yönlendirme middleware mevcut",
    )
    ok(
        're.fullmatch(r"/fiyat-karsilastirma/(\\d+)-(.+)"' in main_text,
        "eski slug URL kalıbı yakalanıyor",
    )
    ok(
        '"/fiyat-karsilastirma/global/{product_ref}"' in main_text,
        "global ürün detay route doğrudan app'e bağlı",
    )
    ok(
        "get_global_product(product_id)" in main_text,
        "global ürün servisi route'a bağlı",
    )
    ok(
        "global_marketplace_product_v14.html" in main_text,
        "global ürün template'i kullanılıyor",
    )

    print(
        "\nFırsatAI v14.9.2 Doğrudan Global Ürün Route "
        "hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
