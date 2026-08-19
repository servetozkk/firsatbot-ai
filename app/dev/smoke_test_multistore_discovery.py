from pathlib import Path
import sys

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from app.services.scan_service import get_cross_store_scan_task
    from app.services.cross_store_search_service import CrossStoreSearchService
    check(callable(get_cross_store_scan_task), "çok mağazalı görev takibi mevcut")
    check(callable(CrossStoreSearchService.scan_other_stores), "çok mağazalı arama motoru mevcut")
    template = (root/"app/templates/product_add.html").read_text(encoding="utf-8")
    check("Tüm mağazalar taranıyor" in template, "ürün ekleme ilerleme paneli mevcut")
    check("scan-tasks" in (root/"app/web/admin_routes.py").read_text(encoding="utf-8"), "görev durum endpointi mevcut")
    cross = (root/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
    check('product_path_patterns=("-p-", "/urun/")' in cross, "Pazarama ürün bağlantısı desteği düzeltildi")
    print("\nÇok Mağazalı Ürün Keşif Motoru smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
