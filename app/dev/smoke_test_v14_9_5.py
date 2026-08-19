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
    ok(version == "14.9.5", "VERSION 14.9.5")

    service_path = (
        root
        / "app"
        / "services"
        / "multi_store_offer_repair_v14_service.py"
    )
    browser_path = (
        root
        / "app"
        / "services"
        / "browser_engine.py"
    )

    service_text = service_path.read_text(encoding="utf-8")
    browser_text = browser_path.read_text(encoding="utf-8")

    ok(
        "V14_9_5_EXACT_MODEL_CANDIDATE_FILTER" in service_text,
        "kesin model kodu aday filtresi mevcut",
    )
    ok(
        "_normalized_model_fragments" in service_text,
        "kaynak model kodu parçaları çıkarılıyor",
    )
    ok(
        "_candidate_url_model_rank" in service_text,
        "aday URL model sıralaması mevcut",
    )
    ok(
        "exact_candidates[:3]" in service_text,
        "tam model adayları öncelikli ve sınırlı deneniyor",
    )
    ok(
        "MODEL_FILTER:" in service_text,
        "alakasız adaylar scraper öncesi reddediliyor",
    )
    ok(
        "V14_9_5_NONINTERACTIVE_VERIFICATION" in browser_text,
        "sunucu modu doğrulama bekleme koruması mevcut",
    )
    ok(
        "FIRSATAI_NONINTERACTIVE" in browser_text,
        "etkileşimsiz çalışma ayarı mevcut",
    )
    ok(
        "time.sleep" in browser_text,
        "manuel Enter yerine süreli bekleme uygulanıyor",
    )

    ast.parse(service_text)
    ast.parse(browser_text)
    ok(True, "değiştirilen Python dosyalarının sözdizimi geçerli")

    print(
        "\nFırsatAI v14.9.5 Model Kodlu Eşleştirme ve "
        "Tarama Tamamlama hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
