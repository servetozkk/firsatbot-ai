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

    ok(
        version == "14.9.3",
        "VERSION 14.9.3",
    )

    service_path = (
        root
        / "app"
        / "services"
        / "multi_store_offer_repair_v14_service.py"
    )
    service_text = service_path.read_text(encoding="utf-8")

    ok(
        'getattr(raw, "specs_raw", None)' in service_text,
        "specs_raw güvenli okunuyor",
    )
    ok(
        'getattr(raw, "specifications", None)' in service_text,
        "alternatif specifications alanı destekleniyor",
    )
    ok(
        'getattr(raw, "attributes", None)' in service_text,
        "alternatif attributes alanı destekleniyor",
    )
    ok(
        'getattr(raw, "details", None)' in service_text,
        "alternatif details alanı destekleniyor",
    )
    ok(
        "or {}" in service_text,
        "teknik özellik yoksa boş sözlükle devam ediliyor",
    )

    ast.parse(service_text)
    ok(
        True,
        "çok mağazalı servis Python sözdizimi geçerli",
    )

    model_path = root / "app" / "database" / "models.py"
    if model_path.exists():
        model_text = model_path.read_text(encoding="utf-8")
        ok(
            "class RawProduct" in model_text,
            "RawProduct modeli mevcut",
        )

    print(
        "\nFırsatAI v14.9.3 RawProduct Şema Uyumluluk "
        "hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
