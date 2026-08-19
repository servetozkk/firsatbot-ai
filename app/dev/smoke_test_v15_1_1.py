from pathlib import Path


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()

    version = (root / "VERSION").read_text(
        encoding="utf-8"
    ).strip()
    ok(version == "15.1.1", "VERSION 15.1.1")

    main_text = (root / "main.py").read_text(encoding="utf-8")

    ok(
        "V15_1_1_DIRECT_MULTI_STORE_API" in main_text,
        "doğrudan API route işareti mevcut",
    )
    ok(
        '@app.post("/api/multi-store-repair/v14/products/{global_product_id}")'
        in main_text,
        "çok mağazalı API doğrudan app'e bağlı",
    )
    ok(
        "candidate_limit: int = 50" in main_text,
        "doğrudan API varsayılan aday limiti 50",
    )
    ok(
        "max(10, min(int(candidate_limit), 50))" in main_text,
        "API aday limiti 10-50 aralığında korunuyor",
    )
    ok(
        "repair_product_across_stores" in main_text,
        "çok mağazalı servis API'ye bağlı",
    )

    print(
        "\nFırsatAI v15.1.1 Çok Mağazalı API Route "
        "Restorasyon smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
