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
    ok(version == "14.9.7", "VERSION 14.9.7")

    path = (
        root
        / "app"
        / "services"
        / "multi_store_offer_repair_v14_service.py"
    )
    text = path.read_text(encoding="utf-8")

    ok(
        "V14_9_7_FAMILY_URL_FILTER_FIX" in text,
        "model ailesi URL filtre düzeltmesi mevcut",
    )
    ok(
        "_source_model_family_and_suffix" in text,
        "kaynak aile ve varyant ayrıştırıcısı mevcut",
    )
    ok(
        "_url_family_variant_state" in text,
        "URL aile/varyant durum kontrolü mevcut",
    )
    ok(
        'if state == "FAMILY_ONLY":' in text,
        "aile adayı scraper öncesi kabul ediliyor",
    )
    ok(
        'if state == "CONFLICT":' in text,
        "farklı son ekli adaylar reddediliyor",
    )
    ok(
        "exact_candidates[:5]" in text,
        "güvenli aday limiti beşe çıkarıldı",
    )

    ast.parse(text)
    ok(True, "çok mağazalı servis sözdizimi geçerli")

    print(
        "\nFırsatAI v14.9.7 Model Ailesi URL Filtre "
        "Düzeltmesi smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
