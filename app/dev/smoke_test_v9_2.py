from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.global_comparison_service import (
    get_global_product_comparison,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    route = (
        ROOT / "app/web/product_group_routes.py"
    ).read_text(encoding="utf-8")
    template = (
        ROOT / "app/templates/product_group_detail_v4.html"
    ).read_text(encoding="utf-8")

    check(
        callable(get_global_product_comparison),
        "global karşılaştırma servisi yüklendi",
    )
    check(
        "global_comparison = get_global_product_comparison(" in route,
        "ürün detay sayfası global teklifleri kullanıyor",
    )
    check(
        "global_comparison or legacy_comparison" in route,
        "eski sisteme güvenli geri dönüş mevcut",
    )
    check(
        "v9-global-data-badge" in template,
        "global katalog veri rozeti mevcut",
    )

    print("\nFırsatAI v9.2 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
