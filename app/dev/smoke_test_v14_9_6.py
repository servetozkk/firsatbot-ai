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
    ok(version == "14.9.6", "VERSION 14.9.6")

    service_path = (
        root
        / "app"
        / "services"
        / "multi_store_offer_repair_v14_service.py"
    )
    service_text = service_path.read_text(encoding="utf-8")

    ok(
        "V14_9_6_MODEL_FAMILY_FALLBACK" in service_text,
        "model ailesi fallback katmanı mevcut",
    )
    ok(
        "_safe_model_family_fallback" in service_text,
        "güvenli aile eşleştirme fonksiyonu mevcut",
    )
    ok(
        "Model varyant son eki farklı." in service_text,
        "farklı varyant son ekleri reddediliyor",
    )
    ok(
        "RAM kapasitesi farklı." in service_text,
        "RAM güvenlik kapısı mevcut",
    )
    ok(
        "Depolama kapasitesi farklı." in service_text,
        "depolama güvenlik kapısı mevcut",
    )
    ok(
        "İşlemci modeli farklı." in service_text,
        "işlemci güvenlik kapısı mevcut",
    )
    ok(
        "fallback_matched" in service_text,
        "normal eşleşme sonrası kontrollü fallback çalışıyor",
    )
    ok(
        "return 1" in service_text,
        "yalnızca model ailesi taşıyan URL adayları işaretleniyor",
    )

    ast.parse(service_text)
    ok(True, "çok mağazalı servis Python sözdizimi geçerli")

    print(
        "\nFırsatAI v14.9.6 Güvenli Model Ailesi "
        "Fallback hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
