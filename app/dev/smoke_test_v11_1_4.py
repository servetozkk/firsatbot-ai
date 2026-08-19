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
    cases = [
        ("Samsung Galaxy A17 5G 256 GB", "Samsung", (None, 256), "5G RAM sayılmıyor"),
        ("Samsung Galaxy A17 4G 128 GB", "Samsung", (None, 128), "4G RAM sayılmıyor"),
        ("Samsung Galaxy A55 5G 8GB/256GB", "Samsung", (8, 256), "telefon 8/256 ayrıştırılıyor"),
        ("Xiaomi Redmi Note 14 Pro 12G+512G 5G", "Xiaomi", (12, 512), "12G+512G korunuyor"),
        ("Apple iPhone 16 Pro 8GB 256GB", "Apple", (8, 256), "iPhone RAM/storage ayrılıyor"),
        ("Lenovo V15 16GB RAM 512SSD", "Lenovo", (16, 512), "512SSD doğru"),
        ("Notebook 32GB RAM 2TB NVMe", "Lenovo", (32, 2048), "2TB NVMe doğru"),
        ("HP Omen Ultra 5-225H 24GB 1TB SSD RTX5050 115W", "HP", (24, 1024), "24GB RAM ve 1TB SSD doğru"),
        ("Xaser 32GB RAM 1TB M.2 NVMe SSD 16GB RX9060 XT", "Xaser", (32, 1024), "M.2 ve RX VRAM filtreleniyor"),
        ("Xaser 32GB RAM 1TB M2 SSD 8GB RTX5060", "Xaser", (32, 1024), "M2 ve RTX VRAM filtreleniyor"),
        ("Casper Nirvana 16GB DDR5 480GB SSD", "Casper", (16, 480), "DDR5 ve 480GB SSD doğru"),
        ("Monster Tulpar 64GB RAM 4TB NVMe RTX 5090", "Monster", (64, 4096), "64GB RAM ve 4TB NVMe doğru"),
        ("Notebook 16GB RAM 1.5TB SSD", "Test", (16, 1536), "ondalıklı TB doğru"),
        ("Notebook RAM: 32GB Depolama: 1024GB SSD", "Test", (32, 1024), "etiketli RAM/storage doğru"),
        ("Notebook Bellek 48GB Disk 2TB NVMe", "Test", (48, 2048), "Bellek ve Disk bağlamı doğru"),
    ]
    for name, brand, expected, message in cases:
        c(pair(name, brand) == expected, message)

    phone_4g = ident("Samsung Galaxy A17 4G 128 GB", "Samsung")
    phone_5g = ident("Samsung Galaxy A17 5G 128 GB", "Samsung")
    c(not validate_variant(phone_4g, phone_5g).compatible, "4G ve 5G varyantları ayrılıyor")

    storage_256 = make("Xiaomi 17 12GB 256GB", "Xiaomi")
    storage_512 = make("Xiaomi 17 12GB 512GB", "Xiaomi")
    c(not validate_variant(ProductIdentityService.parse(storage_256), ProductIdentityService.parse(storage_512)).compatible,
      "256GB ile 512GB ayrılıyor")
    matched, _, _ = CrossStoreSearchService._is_same_product(storage_256, storage_512)
    c(not matched, "Cross Store Matching farklı storage reddediyor")

    ram_16 = make("Notebook 16GB RAM 1TB SSD", "Test")
    ram_32 = make("Notebook 32GB RAM 1TB SSD", "Test")
    c(not validate_variant(ProductIdentityService.parse(ram_16), ProductIdentityService.parse(ram_32)).compatible,
      "16GB ile 32GB RAM ayrılıyor")

    c((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "11.1.4", "VERSION 11.1.4")
    print("\nFırsatAI v11.1.4 geniş regresyon testi başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
