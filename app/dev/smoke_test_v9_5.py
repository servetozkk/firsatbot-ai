from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.services.global_variant_service import get_product_variants
from app.services.global_comparison_service import get_global_product_comparison

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    route = (ROOT / "app/web/product_group_routes.py").read_text(encoding="utf-8")
    template = (ROOT / "app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    check(callable(get_product_variants), "global varyant servisi yüklendi")
    check(callable(get_global_product_comparison), "varyant destekli karşılaştırma servisi yüklendi")
    check("selected_variant_id=variant" in route, "ürün detay route'u varyant seçimini kullanıyor")
    check("v9-variant-selector" in template, "ürün detayında varyant seçici mevcut")
    print("\nFırsatAI v9.5 smoke test başarılı.")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
