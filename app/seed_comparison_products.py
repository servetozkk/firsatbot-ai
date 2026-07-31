from __future__ import annotations

import json
from datetime import datetime

from app.database.database import SessionLocal
from app.database.models import ProductDB
from app.models.product import Product
from app.services.multi_store_service import sync_product_offer


DEMO_PRODUCTS = [
    {
        "name": "Fırsat AI Demo AlphaBook G16 RTX 4060",
        "price": 48999.00,
        "old_price": 52999.00,
        "rating": 4.6,
        "review_count": 184,
        "seller": "Demo Teknoloji",
        "url": "https://demo.firsatai.local/alphabook-g16-rtx4060",
        "image": None,
        "brand": "AlphaBook",
        "model": "G16-4060",
        "category": "Laptop",
        "description": "Karşılaştırma motoru için oluşturulmuş demo oyuncu laptopu.",
        "stock_status": "Stokta",
        "source_site": "demo",
        "product_code": "DEMO-ALPHA-G16-4060",
        "specifications": {
            "İşlemci": "Intel Core i7-14650HX",
            "İşlemci Çekirdek Sayısı": "16",
            "İşlemci Maksimum Hızı": "5.2 GHz",
            "RAM Kapasitesi": "16 GB",
            "RAM Tipi": "DDR5",
            "RAM Hızı": "5600 MHz",
            "SSD Kapasitesi": "1 TB",
            "Ekran Kartı": "NVIDIA GeForce RTX 4060",
            "Ekran Kartı Belleği": "8 GB",
            "Ekran Boyutu": "16 inç",
            "Ekran Çözünürlüğü": "2560 x 1600",
            "Yenileme Hızı": "165 Hz",
            "Panel Tipi": "IPS",
            "Parlaklık": "350 nit",
            "Renk Gamı": "%100 sRGB",
            "İşletim Sistemi": "FreeDOS",
            "Ağırlık": "2.30 kg",
            "Kalınlık": "24.5 mm",
            "Batarya Kapasitesi": "80 Wh",
            "Wi-Fi 6E": "Var",
            "Bluetooth": "5.3",
            "Ethernet": "Var",
            "HDMI 2.1": "Var",
            "Thunderbolt 4": "Var",
            "USB-C": "2",
            "Klavye Aydınlatması": "RGB",
            "Web Kamera": "1080p",
        },
    },
    {
        "name": "Fırsat AI Demo Nova Gaming N15 RTX 4050",
        "price": 41999.00,
        "old_price": 45999.00,
        "rating": 4.4,
        "review_count": 96,
        "seller": "Demo Bilgisayar",
        "url": "https://demo.firsatai.local/nova-n15-rtx4050",
        "image": None,
        "brand": "Nova",
        "model": "N15-4050",
        "category": "Laptop",
        "description": "Karşılaştırma motoru için oluşturulmuş demo oyuncu laptopu.",
        "stock_status": "Stokta",
        "source_site": "demo",
        "product_code": "DEMO-NOVA-N15-4050",
        "specifications": {
            "İşlemci": "Intel Core i7-13620H",
            "İşlemci Çekirdek Sayısı": "10",
            "İşlemci Maksimum Hızı": "4.9 GHz",
            "RAM Kapasitesi": "16 GB",
            "RAM Tipi": "DDR5",
            "RAM Hızı": "4800 MHz",
            "SSD Kapasitesi": "512 GB",
            "Ekran Kartı": "NVIDIA GeForce RTX 4050",
            "Ekran Kartı Belleği": "6 GB",
            "Ekran Boyutu": "15.6 inç",
            "Ekran Çözünürlüğü": "1920 x 1080",
            "Yenileme Hızı": "144 Hz",
            "Panel Tipi": "IPS",
            "Parlaklık": "300 nit",
            "Renk Gamı": "%62.5 sRGB",
            "İşletim Sistemi": "FreeDOS",
            "Ağırlık": "2.20 kg",
            "Kalınlık": "25.0 mm",
            "Batarya Kapasitesi": "60 Wh",
            "Wi-Fi 6E": "Yok",
            "Bluetooth": "5.2",
            "Ethernet": "Var",
            "HDMI 2.1": "Var",
            "Thunderbolt 4": "Yok",
            "USB-C": "1",
            "Klavye Aydınlatması": "Tek renk",
            "Web Kamera": "720p",
        },
    },
    {
        "name": "Fırsat AI Demo Vertex Pro 16 RTX 4070",
        "price": 64999.00,
        "old_price": 69999.00,
        "rating": 4.8,
        "review_count": 71,
        "seller": "Demo Premium",
        "url": "https://demo.firsatai.local/vertex-pro16-rtx4070",
        "image": None,
        "brand": "Vertex",
        "model": "PRO16-4070",
        "category": "Laptop",
        "description": "Karşılaştırma motoru için oluşturulmuş üst seviye demo laptop.",
        "stock_status": "Stokta",
        "source_site": "demo",
        "product_code": "DEMO-VERTEX-PRO16-4070",
        "specifications": {
            "İşlemci": "AMD Ryzen 9 8945HX",
            "İşlemci Çekirdek Sayısı": "16",
            "İşlemci Maksimum Hızı": "5.4 GHz",
            "RAM Kapasitesi": "32 GB",
            "RAM Tipi": "DDR5",
            "RAM Hızı": "5600 MHz",
            "SSD Kapasitesi": "2 TB",
            "Ekran Kartı": "NVIDIA GeForce RTX 4070",
            "Ekran Kartı Belleği": "8 GB",
            "Ekran Boyutu": "16 inç",
            "Ekran Çözünürlüğü": "2560 x 1600",
            "Yenileme Hızı": "240 Hz",
            "Panel Tipi": "Mini LED",
            "Parlaklık": "500 nit",
            "Renk Gamı": "%100 DCI-P3",
            "İşletim Sistemi": "Windows 11",
            "Ağırlık": "2.45 kg",
            "Kalınlık": "26.0 mm",
            "Batarya Kapasitesi": "90 Wh",
            "Wi-Fi 6E": "Var",
            "Bluetooth": "5.3",
            "Ethernet": "Var",
            "HDMI 2.1": "Var",
            "Thunderbolt 4": "Yok",
            "USB-C": "2",
            "Klavye Aydınlatması": "RGB",
            "Web Kamera": "1080p",
        },
    },
    {
        "name": "Fırsat AI Demo AirLite 14 RTX 4050",
        "price": 53999.00,
        "old_price": 57999.00,
        "rating": 4.7,
        "review_count": 128,
        "seller": "Demo Mobil",
        "url": "https://demo.firsatai.local/airlite14-rtx4050",
        "image": None,
        "brand": "AirLite",
        "model": "A14-4050",
        "category": "Laptop",
        "description": "Hafiflik ve taşınabilirlik odaklı karşılaştırma demo laptopu.",
        "stock_status": "Stokta",
        "source_site": "demo",
        "product_code": "DEMO-AIRLITE-A14-4050",
        "specifications": {
            "İşlemci": "AMD Ryzen 7 8845HS",
            "İşlemci Çekirdek Sayısı": "8",
            "İşlemci Maksimum Hızı": "5.1 GHz",
            "RAM Kapasitesi": "32 GB",
            "RAM Tipi": "LPDDR5X",
            "RAM Hızı": "6400 MHz",
            "SSD Kapasitesi": "1 TB",
            "Ekran Kartı": "NVIDIA GeForce RTX 4050",
            "Ekran Kartı Belleği": "6 GB",
            "Ekran Boyutu": "14 inç",
            "Ekran Çözünürlüğü": "2880 x 1800",
            "Yenileme Hızı": "120 Hz",
            "Panel Tipi": "OLED",
            "Parlaklık": "500 nit",
            "Renk Gamı": "%100 DCI-P3",
            "İşletim Sistemi": "Windows 11",
            "Ağırlık": "1.55 kg",
            "Kalınlık": "17.9 mm",
            "Batarya Kapasitesi": "76 Wh",
            "Wi-Fi 6E": "Var",
            "Bluetooth": "5.3",
            "Ethernet": "Yok",
            "HDMI 2.1": "Var",
            "Thunderbolt 4": "Yok",
            "USB-C": "2",
            "Klavye Aydınlatması": "Beyaz",
            "Web Kamera": "1080p",
        },
    },
]


def create_product_model(item: dict) -> Product:
    return Product(
        name=item["name"],
        price=item["price"],
        old_price=item["old_price"],
        rating=item["rating"],
        review_count=item["review_count"],
        seller=item["seller"],
        url=item["url"],
        image=item["image"],
        brand=item["brand"],
        model=item["model"],
        category=item["category"],
        description=item["description"],
        specifications=json.dumps(
            item["specifications"],
            ensure_ascii=False,
        ),
        stock_status=item["stock_status"],
        source_site=item["source_site"],
        product_code=item["product_code"],
    )


def upsert_database_product(db, product: Product) -> tuple[ProductDB, bool]:
    existing = (
        db.query(ProductDB)
        .filter(ProductDB.url == product.url)
        .first()
    )

    now = datetime.utcnow()

    if existing:
        old_price = float(existing.price)
        new_price = float(product.price)
        price_changed = abs(old_price - new_price) >= 0.01

        existing.name = product.name
        existing.price = new_price
        existing.old_price = product.old_price
        existing.rating = product.rating
        existing.review_count = product.review_count
        existing.seller = product.seller
        existing.image = str(product.image) if product.image else None
        existing.brand = product.brand
        existing.model = product.model
        existing.category = product.category
        existing.description = product.description
        existing.specifications = product.specifications
        existing.stock_status = product.stock_status
        existing.source_site = product.source_site
        existing.product_code = product.product_code
        existing.updated_at = now

        if price_changed:
            existing.last_price_change = now

        db.flush()
        return existing, price_changed

    database_product = ProductDB(
        name=product.name,
        price=float(product.price),
        old_price=product.old_price,
        rating=product.rating,
        review_count=product.review_count,
        seller=product.seller,
        url=product.url,
        image=str(product.image) if product.image else None,
        ai_score=0,
        last_notified_price=None,
        brand=product.brand,
        model=product.model,
        category=product.category,
        description=product.description,
        specifications=product.specifications,
        stock_status=product.stock_status,
        source_site=product.source_site,
        product_code=product.product_code,
        created_at=now,
        updated_at=now,
    )

    db.add(database_product)
    db.flush()

    return database_product, True


def main() -> None:
    db = SessionLocal()

    added = 0
    updated = 0

    try:
        for item in DEMO_PRODUCTS:
            product = create_product_model(item)

            database_product, price_changed = upsert_database_product(
                db,
                product,
            )

            was_existing = database_product.created_at != database_product.updated_at

            sync_product_offer(
                db=db,
                database_product=database_product,
                product=product,
                price_changed=price_changed,
            )

            if was_existing:
                updated += 1
                status = "GÜNCELLENDİ"
            else:
                added += 1
                status = "EKLENDİ"

            print(
                f"[{status}] {product.name} - "
                f"{len(item['specifications'])} özellik"
            )

        db.commit()

        print("-" * 70)
        print("Demo ürün aktarımı tamamlandı.")
        print("Eklenen:", added)
        print("Güncellenen:", updated)
        print("Toplam:", len(DEMO_PRODUCTS))

    except Exception as error:
        db.rollback()
        print("Demo ürün aktarımı başarısız:", error)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
