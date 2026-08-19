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
    ok(version == "15.1.0", "VERSION 15.1.0")

    service_path = (
        root
        / "app"
        / "services"
        / "multi_store_offer_repair_v14_service.py"
    )
    route_path = (
        root
        / "app"
        / "web"
        / "multi_store_offer_repair_v14_routes.py"
    )

    service_text = service_path.read_text(encoding="utf-8")
    route_text = route_path.read_text(encoding="utf-8")

    ok(
        "V15_1_CANDIDATE_COLLECTION_ENGINE" in service_text,
        "V15.1 aday toplama motoru mevcut",
    )
    ok(
        "_is_obvious_non_product_url" in service_text,
        "ürün olmayan bağlantı filtresi mevcut",
    )
    ok(
        "_candidate_sort_key" in service_text,
        "URL aday sıralama anahtarı mevcut",
    )
    ok(
        "Rank 0 adaylar da scraper" in service_text,
        "rank 0 adaylar artık erken reddedilmiyor",
    )
    ok(
        "MODEL_FILTER: URL kaynak model kodunu taşımıyor" not in service_text,
        "eski URL tabanlı kesin red kaldırıldı",
    )
    ok(
        "candidate_limit: int = 50" in service_text,
        "servis aday limiti 50",
    )
    ok(
        "Query(50, ge=10, le=50)" in route_text,
        "API aday limiti 50",
    )

    ast.parse(service_text)
    ast.parse(route_text)
    ok(True, "değiştirilen Python dosyalarının sözdizimi geçerli")

    print(
        "\nFırsatAI v15.1.0 Aday Toplama Motoru "
        "smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
