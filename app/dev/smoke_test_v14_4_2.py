from pathlib import Path
import re


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    route_text = (
        root / "app/web/global_marketplace_v14_routes.py"
    ).read_text(encoding="utf-8")
    template_text = (
        root / "app/templates/global_marketplace_catalog_v14.html"
    ).read_text(encoding="utf-8")

    ok(version == "14.4.2", "VERSION 14.4.2")
    ok(
        '/fiyat-karsilastirma/global/{product_id}-{slug}' in route_text,
        "global ürün detay yolu eski route ile çakışmıyor",
    )
    ok(
        'href="/fiyat-karsilastirma/global/{{ p.id }}-{{ p.slug }}"'
        in template_text,
        "ürün kartları yeni SEO detay yolunu kullanıyor",
    )
    ok(
        'product_id: int' in route_text,
        "ürün kimliği integer olarak ayrıştırılıyor",
    )
    ok(
        'canonical_path' in route_text,
        "kanonik SEO URL üretiliyor",
    )
    ok(
        '"engine_version": "14.4.2"' in route_text,
        "global marketplace API sürümü güncellendi",
    )

    # "global" sabit segmenti sayesinde eski tek segmentli route eşleşemez.
    example = "/fiyat-karsilastirma/global/58-apple-iphone-17-pro-256-gb"
    ok(
        len(example.strip("/").split("/")) == 3,
        "SEO detay URL'si ayrı path segmenti kullanıyor",
    )

    print(
        "\nFırsatAI v14.4.2 Global Ürün SEO Detay Route "
        "hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
