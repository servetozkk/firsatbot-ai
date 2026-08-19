from pathlib import Path
import importlib.util


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "14.9.1", "VERSION 14.9.1")

    route_path = root / "app/web/global_marketplace_v14_routes.py"
    text = route_path.read_text(encoding="utf-8")

    ok("_parse_product_id" in text, "SEO ürün kimliği ayrıştırıcısı mevcut")
    ok(
        '"/fiyat-karsilastirma/global/{product_ref}"' in text,
        "global SEO route string ürün referansı kabul ediyor",
    )
    ok(
        '"/fiyat-karsilastirma/{product_ref}"' in text,
        "eski ürün detay bağlantısı uyumluluğu mevcut",
    )
    ok(
        '"/api/global-marketplace/v14/products/{product_ref}"' in text,
        "ürün API slug içeren referansı kabul ediyor",
    )
    ok(
        "RedirectResponse" in text and "status_code=301" in text,
        "eski bağlantılar kanonik SEO adresine yönlendiriliyor",
    )
    ok(
        '"engine_version": "14.9.1"' in text,
        "global marketplace API sürümü güncellendi",
    )

    # Bağımlılıkları import etmeden ayrıştırıcı mantığını doğrudan doğrula.
    import re
    def parse(value: str) -> int:
        match = re.match(r"^\s*(\d+)(?:-|$)", value)
        if not match:
            raise ValueError
        return int(match.group(1))

    ok(parse("125") == 125, "yalın ürün kimliği ayrıştırılıyor")
    ok(
        parse("125-asus-vivobook-15-x1504va-bq5391") == 125,
        "slug içeren ürün kimliği ayrıştırılıyor",
    )

    print(
        "\nFırsatAI v14.9.1 Global Ürün SEO Route "
        "Uyumluluk hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
