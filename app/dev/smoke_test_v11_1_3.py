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

def make(name: str, brand: str = "Test") -> Product:
    return Product(name=name, price=100, old_price=None, rating=None,
        review_count=None, seller="Test", url="https://test.invalid/item",
        image=None, brand=brand, model=None, category="Test")

def c(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def ident(name, brand="Test"):
    return ProductIdentityService.parse(make(name, brand))

def pair(name, brand="Test"):
    p = ident(name, brand)
    return p.ram_gb, p.storage_gb

def main() -> int:
    c(pair("Samsung Galaxy A17 5G 256 GB", "Samsung") == (None, 256), "5G RAM sayılmıyor")
    c(pair("Lenovo V15 16GB RAM 512SSD", "Lenovo") == (16, 512), "512SSD doğru")
    c(pair("Notebook 32GB RAM 2TB NVMe", "Lenovo") == (32, 2048), "2TB NVMe doğru")
    c(pair("HP Omen Ultra 5-225H 24GB 1TB SSD RTX5050 115W", "HP") == (24, 1024), "24GB RAM ve 1TB SSD doğru")
    c(pair("Xaser Ryzen 7 5700X 32GB RAM 1TB M.2 NVMe SSD 16GB RX9060 XT", "Xaser") == (32, 1024), "M.2 kapasite sayılmıyor")
    c(pair("Xaser Ryzen 7 5700X 32GB RAM 1TB M.2 SSD 8GB RTX5060", "Xaser") == (32, 1024), "RTX VRAM sistem RAM'ine karışmıyor")
    c(pair("Zeiron Ryzen 7 5700X 32GB RAM 1TB M.2 SSD 16GB RTX5060Ti", "Zeiron") == (32, 1024), "16GB GPU VRAM ayrılıyor")
    c(pair("Casper Nirvana i7-13620H 16GB DDR5 480GB SSD FreeDOS", "Casper") == (16, 480), "DDR5 RAM ve 480GB SSD doğru")
    c(pair("Monster Tulpar 16GB RAM 1TB SSD RTX 5060", "Monster") == (16, 1024), "RTX model numarası kapasite sayılmıyor")
    source=make("Bilgisayar 32GB RAM 1TB M.2 SSD RTX5060", "Test")
    wrong=make("Bilgisayar 64GB RAM 1TB M.2 SSD RTX5060", "Test")
    c(not validate_variant(ProductIdentityService.parse(source), ProductIdentityService.parse(wrong)).compatible, "32GB ile 64GB RAM ayrılıyor")
    matched,_,_=CrossStoreSearchService._is_same_product(source,wrong)
    c(not matched, "Cross Store Matching farklı RAM'i reddediyor")
    c((ROOT/'VERSION').read_text(encoding='utf-8').strip()=='11.1.3', 'VERSION 11.1.3')
    print('\nFırsatAI v11.1.3 smoke test başarılı.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
