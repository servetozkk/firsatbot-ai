from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.6.1", "VERSION 13.6.1")

    from app.services.schema_org_service import (
        breadcrumb_schema,
        dumps,
        product_schema,
        website_schema,
    )

    site = website_schema("https://firsatai.example/")
    ok(site["@type"] == "WebSite", "WebSite şeması mevcut")
    ok(site["potentialAction"]["@type"] == "SearchAction", "SearchAction şeması mevcut")

    crumbs = breadcrumb_schema("https://firsatai.example/", [("Ana sayfa", "/"), ("Laptop", "/kategori/laptop")])
    ok(crumbs["@type"] == "BreadcrumbList" and len(crumbs["itemListElement"]) == 2, "BreadcrumbList şeması mevcut")

    group = SimpleNamespace(canonical_name="Lenovo LOQ 15", brand="Lenovo", category="Laptop", group_key="abc123")
    single = product_schema(
        base_url="https://firsatai.example/",
        canonical_url="https://firsatai.example/urun/lenovo-loq-15-p-abc123",
        group=group,
        comparison={"product_name": "Lenovo LOQ 15"},
        available_offers=[{"total_price": 39999, "store": "Örnek Mağaza", "url": "https://store.example/item", "is_available": True}],
        image_urls=["/static/product.jpg"],
    )
    ok(single["@type"] == "Product", "Product şeması mevcut")
    ok(single["offers"]["@type"] == "Offer", "tek teklif Offer olarak üretiliyor")

    aggregate = product_schema(
        base_url="https://firsatai.example/",
        canonical_url="https://firsatai.example/urun/lenovo-loq-15-p-abc123",
        group=group,
        comparison={},
        available_offers=[
            {"total_price": 39999, "store": "A", "is_available": True},
            {"total_price": 41999, "store": "B", "is_available": True},
        ],
    )
    ok(aggregate["offers"]["@type"] == "AggregateOffer", "çoklu teklif AggregateOffer olarak üretiliyor")
    ok(aggregate["offers"]["lowPrice"] == "39999.00", "AggregateOffer düşük fiyatı doğru")
    ok(aggregate["offers"]["offerCount"] == 2, "AggregateOffer teklif sayısı doğru")

    no_offer = product_schema(
        base_url="https://firsatai.example/",
        canonical_url="https://firsatai.example/urun/lenovo-loq-15-p-abc123",
        group=group,
        comparison={},
        available_offers=[{"total_price": None, "store": "A"}],
    )
    ok("offers" not in no_offer, "geçersiz fiyat için sahte Offer üretilmiyor")
    json.loads(dumps(aggregate))
    ok(True, "Schema JSON geçerli JSON olarak üretiliyor")

    base = (ROOT / "app/templates/public_base.html").read_text(encoding="utf-8-sig")
    route = (ROOT / "app/web/product_group_routes.py").read_text(encoding="utf-8-sig")
    ok('type="application/ld+json"' in base, "JSON-LD script etiketleri template içinde mevcut")
    ok("product_schema_json" in route and "breadcrumb_schema_json" in route, "ürün route'u Schema.org context üretimine bağlı")
    print("\nFırsatAI v13.6.1 Schema.org smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
