from pathlib import Path
import ast


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(
        encoding="utf-8"
    ).strip()
    ok(version == "15.1.3", "VERSION 15.1.3")

    main_text = (root / "main.py").read_text(encoding="utf-8")
    ast.parse(main_text)

    ok(
        "V15_1_3_RUNTIME_IDENTITY" in main_text,
        "runtime kimlik işareti mevcut",
    )
    ok(
        '"/api/runtime-identity/v1513"' in main_text,
        "runtime kimlik endpoint'i mevcut",
    )
    ok(
        "canonical_multi_store_repair_v1512" in main_text,
        "kanonik çok mağazalı POST route korunuyor",
    )

    print(
        "\nFırsatAI v15.1.3 Doğru Proje Çalıştırıcı "
        "smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
