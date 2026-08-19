from pathlib import Path
import ast

from app.models.product import Product
from app.services.weighted_product_matcher_v15 import (
    match_products_v15,
)


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def product(name: str, model: str | None = None) -> Product:
    return Product(
        name=name,
        price=1.0,
        old_price=None,
        rating=0.0,
        review_count=0,
        seller="Test",
        url="https://example.com/test",
        image=None,
        brand="Asus",
        model=model,
    )


def main() -> int:
    root = Path.cwd()

    version = (root / "VERSION").read_text(
        encoding="utf-8"
    ).strip()
    ok(version == "15.0.0", "VERSION 15.0.0")

    matcher_path = (
        root
        / "app"
        / "services"
        / "weighted_product_matcher_v15.py"
    )
    service_path = (
        root
        / "app"
        / "services"
        / "multi_store_offer_repair_v14_service.py"
    )

    matcher_text = matcher_path.read_text(encoding="utf-8")
    service_text = service_path.read_text(encoding="utf-8")

    ast.parse(matcher_text)
    ast.parse(service_text)

    ok(
        "match_products_v15" in service_text,
        "V15 motoru çok mağazalı servise bağlı",
    )
    ok(
        "candidate_limit: int = 20" in service_text,
        "varsayılan aday limiti 20",
    )
    ok(
        "minimum_score=0.72" in service_text,
        "V15 güvenli eşik 0.72",
    )

    source = product(
        "ASUS Vivobook 15 X1504VA-BQ5391 "
        "Intel Core 5 120U 8GB RAM 512GB SSD 15.6 FHD",
        "X1504VA-BQ5391",
    )

    pazarama = product(
        "Asus Vivobook 15 X1504VA Laptop "
        "Intel Core i5 120U 8GB RAM 512GB SSD 15.6 inch",
        "X1504VA",
    )

    wrong_variant = product(
        "ASUS Vivobook 15 X1504VA-BQ5385 "
        "Intel Core 5 120U 8GB RAM 512GB SSD 15.6 FHD",
        "X1504VA-BQ5385",
    )

    wrong_storage = product(
        "ASUS Vivobook 15 X1504VA "
        "Intel Core 5 120U 8GB RAM 1TB SSD 15.6 FHD",
        "X1504VA",
    )

    matched, score, reason = match_products_v15(
        source_product=source,
        candidate_product=pazarama,
    )
    ok(
        matched,
        f"Pazarama aile ve donanım adayı eşleşti: {score} {reason}",
    )
    ok(score >= 0.72, "Pazarama adayı güvenli eşiği geçti")

    matched, score, reason = match_products_v15(
        source_product=source,
        candidate_product=wrong_variant,
    )
    ok(
        not matched,
        "farklı BQ5385 varyantı reddedildi",
    )

    matched, score, reason = match_products_v15(
        source_product=source,
        candidate_product=wrong_storage,
    )
    ok(
        not matched,
        "1 TB farklı depolama varyantı reddedildi",
    )

    print(
        "\nFırsatAI v15.0.0 Ağırlıklı Akakçe Eşleştirme "
        "Motoru smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
