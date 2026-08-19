from pathlib import Path
import ast

from app.services.multi_store_offer_repair_v14_service import (
    _candidate_url_model_rank,
    _source_model_family_and_suffix,
    _url_family_variant_state,
    product_from_global_product,
)


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(
        encoding="utf-8"
    ).strip()
    ok(version == "14.9.7", "VERSION 14.9.7 korunuyor")

    service_path = (
        root
        / "app"
        / "services"
        / "multi_store_offer_repair_v14_service.py"
    )
    service_text = service_path.read_text(encoding="utf-8")

    ok(
        "_source_model_family_and_suffix" in service_text,
        "kaynak aile ve varyant ayrıştırıcısı mevcut",
    )
    ok(
        "_url_family_variant_state" in service_text,
        "URL aile/varyant durum kontrolü mevcut",
    )
    ok(
        "_candidate_url_model_rank" in service_text,
        "aday URL sıralama fonksiyonu mevcut",
    )

    ast.parse(service_text)
    ok(True, "çok mağazalı servis sözdizimi geçerli")

    product = product_from_global_product(125)
    family, suffix = _source_model_family_and_suffix(product)

    ok(
        family == "x1504va",
        f"kaynak model ailesi doğru çıkarıldı: {family}",
    )
    ok(
        suffix == "bq5391",
        f"kaynak varyant son eki doğru çıkarıldı: {suffix}",
    )

    pazarama_url = (
        "https://www.pazarama.com/"
        "asus-vivobook-15-x1504va-laptop-intel-core-i5-120u-"
        "8gb-ram-512gb-ssd-15-6-inch-p-1"
    )
    conflicting_url = (
        "https://www.teknosa.com/"
        "asus-vivobook-x1504va-bq5385-p-1"
    )
    exact_url = (
        "https://www.hepsiburada.com/"
        "asus-vivobook-x1504va-bq5391-pm-test"
    )

    ok(
        _url_family_variant_state(
            candidate_url=pazarama_url,
            source_product=product,
        ) == "FAMILY_ONLY",
        "Pazarama aile kodlu aday FAMILY_ONLY olarak tanındı",
    )
    ok(
        _candidate_url_model_rank(
            candidate_url=pazarama_url,
            source_product=product,
        ) >= 2,
        "Pazarama aile adayı scraper öncesi kabul ediliyor",
    )
    ok(
        _url_family_variant_state(
            candidate_url=conflicting_url,
            source_product=product,
        ) == "CONFLICT",
        "farklı Teknosa varyantı CONFLICT olarak tanındı",
    )
    ok(
        _candidate_url_model_rank(
            candidate_url=conflicting_url,
            source_product=product,
        ) == 0,
        "farklı Teknosa varyantı reddediliyor",
    )
    ok(
        _candidate_url_model_rank(
            candidate_url=exact_url,
            source_product=product,
        ) >= 3,
        "tam Hepsiburada model kodu en yüksek öncelikte",
    )

    print(
        "\nFırsatAI v14.9.7A Model Ailesi URL Filtre "
        "doğrulama hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
