from pathlib import Path
import ast
import inspect

from app.models.product import Product


def ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    root = Path.cwd()
    version = (root / "VERSION").read_text(
        encoding="utf-8"
    ).strip()

    ok(version == "14.9.4", "VERSION 14.9.4")

    signature = inspect.signature(Product)
    required = {
        name
        for name, parameter in signature.parameters.items()
        if parameter.default is inspect.Parameter.empty
    }

    ok("rating" in required, "Product rating alanı zorunlu")
    ok(
        "review_count" in required,
        "Product review_count alanı zorunlu",
    )

    service_path = (
        root
        / "app"
        / "services"
        / "multi_store_offer_repair_v14_service.py"
    )
    service_text = service_path.read_text(encoding="utf-8")

    ok(
        'getattr(raw, "rating", None)' in service_text,
        "RawProduct rating alanı güvenli okunuyor",
    )
    ok(
        'getattr(raw, "rating_raw", None)' in service_text,
        "rating_raw alternatifi destekleniyor",
    )
    ok(
        'getattr(raw, "review_count", None)' in service_text,
        "RawProduct review_count güvenli okunuyor",
    )
    ok(
        'getattr(raw, "review_count_raw", None)' in service_text,
        "review_count_raw alternatifi destekleniyor",
    )
    ok(
        "or 0.0" in service_text,
        "rating bulunamazsa güvenli varsayılan kullanılıyor",
    )
    ok(
        "or 0" in service_text,
        "review_count bulunamazsa güvenli varsayılan kullanılıyor",
    )

    ast.parse(service_text)
    ok(True, "çok mağazalı servis Python sözdizimi geçerli")

    # Gerçek Product constructor sözleşmesini minimal örnekle doğrula.
    product = Product(
        name="Test ürün",
        price=1.0,
        old_price=None,
        rating=0.0,
        review_count=0,
        seller="Test satıcı",
        url="https://example.com/test",
        image=None,
    )
    ok(product.rating == 0.0, "Product rating varsayılanı kabul ediyor")
    ok(
        product.review_count == 0,
        "Product review_count varsayılanı kabul ediyor",
    )

    print(
        "\nFırsatAI v14.9.4 Product Constructor Uyumluluk "
        "hotfix smoke test başarılı."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
