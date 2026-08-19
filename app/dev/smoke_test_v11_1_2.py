from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService
from app.services.offer_integrity_service import validate_variant
from app.services.cross_store_search_service import CrossStoreSearchService

def make(name: str, brand: str = "Samsung") -> Product:
    return Product(name=name, price=100, old_price=None, rating=None,
        review_count=None, seller="Test", url="https://test.invalid/item",
        image=None, brand=brand, model=None, category="Test")

def c(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def ident(name, brand="Samsung"):
    return ProductIdentityService.parse(make(name, brand))

def main() -> int:
    a=ident("Samsung Galaxy A17 5G 256 GB")
    c(a.network == "5g", "5G şebeke olarak algılanıyor")
    c(a.ram_gb is None, "5G RAM sayılmıyor")
    c(a.storage_gb == 256, "Galaxy depolama 256 GB")
    c((ident("Xiaomi 17 12G512GB", "Xiaomi").ram_gb, ident("Xiaomi 17 12G512GB", "Xiaomi").storage_gb)==(12,512), "12G512GB korunuyor")
    c((ident("Xiaomi 17 12G+256G", "Xiaomi").ram_gb, ident("Xiaomi 17 12G+256G", "Xiaomi").storage_gb)==(12,256), "12G+256G korunuyor")
    b=ident("Lenovo V15 Ryzen 5 7520U 16GB RAM 512SSD", "Lenovo")
    c(b.ram_gb == 16, "16GB RAM doğru")
    c(b.storage_gb == 512, "512SSD başlık önceliği")
    c(ident("Notebook 16GB RAM 1TB NVMe", "Lenovo").storage_gb == 1024, "1TB NVMe doğru")
    c(ident("Notebook 32GB RAM 2TB NVMe", "Lenovo").storage_gb == 2048, "2TB NVMe doğru")
    c(ident("Notebook 16GB RAM 512 GB SSD", "Lenovo").storage_gb == 512, "512 GB SSD doğru")
    source=make("Xiaomi 17 12G+256G", "Xiaomi")
    wrong=make("Xiaomi 17 12G+512G", "Xiaomi")
    c(not validate_variant(ProductIdentityService.parse(source), ProductIdentityService.parse(wrong)).compatible, "256 GB ile 512 GB ayrılıyor")
    matched,_,_=CrossStoreSearchService._is_same_product(source,wrong)
    c(not matched, "Cross Store Matching farklı storage reddediyor")
    c((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='11.1.2', 'VERSION 11.1.2')
    print('\nFırsatAI v11.1.2 smoke test başarılı.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
