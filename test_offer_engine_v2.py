"""Offer Engine V2 entegrasyon testi.

Canlı proje veritabanına dokunmaz. Geçici SQLite veritabanında:
- aynı kimlikte iki mağaza ürününün tek grupta birleşmesini,
- iki ayrı teklif oluşmasını,
- en ucuz teklif işaretini,
- fiyat değişiminde yeni teklif yerine fiyat geçmişi eklenmesini test eder.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.database.models import (
    OfferPriceHistory,
    ProductDB,
    ProductGroup,
    ProductOffer,
)
from app.models.product import Product
from app.services.multi_store_service import (
    calculate_group_comparison,
    sync_product_offer,
)


def make_product(*, source: str, url: str, price: float) -> Product:
    return Product(
        name="Samsung Fold8 Ultra 5G 1TB Gri Akıllı Telefon",
        price=price,
        old_price=None,
        rating=4.8,
        review_count=120,
        seller=source.title(),
        url=url,
        image=None,
        brand="Samsung",
        model=None,
        category="Cep Telefonu",
        description=None,
        specifications={"Depolama": "1 TB", "Bağlantı": "5G"},
        stock_status="Stokta",
        source_site=source,
        product_code=f"{source}-fold8-ultra-1tb",
    )


def persist_store_product(db, product: Product) -> ProductDB:
    now = datetime.utcnow()
    record = ProductDB(
        name=product.name,
        price=float(product.price),
        old_price=product.old_price,
        rating=product.rating,
        review_count=product.review_count,
        seller=product.seller,
        url=product.url,
        image=product.image,
        ai_score=0,
        brand=product.brand,
        model=product.model,
        category=product.category,
        stock_status=product.stock_status,
        source_site=product.source_site,
        product_code=product.product_code,
        last_price_change=now,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.flush()
    return record


def main() -> None:
    with TemporaryDirectory(prefix="offer_engine_v2_") as temp_dir:
        database_path = Path(temp_dir) / "test.db"
        engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False},
        )
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=engine)

        db = Session()
        try:
            teknosa = make_product(
                source="teknosa",
                url="https://www.teknosa.com/fold8-ultra-1tb-p-1",
                price=79_999.0,
            )
            trendyol = make_product(
                source="trendyol",
                url="https://www.trendyol.com/samsung/fold8-ultra-1tb-p-2",
                price=77_499.0,
            )

            teknosa_db = persist_store_product(db, teknosa)
            sync_product_offer(db, teknosa_db, teknosa, price_changed=True)

            trendyol_db = persist_store_product(db, trendyol)
            sync_product_offer(db, trendyol_db, trendyol, price_changed=True)
            db.commit()

            groups = db.query(ProductGroup).all()
            offers = db.query(ProductOffer).order_by(ProductOffer.current_price).all()

            assert len(groups) == 1, f"Beklenen grup sayısı 1, bulunan: {len(groups)}"
            assert len(offers) == 2, f"Beklenen teklif sayısı 2, bulunan: {len(offers)}"
            assert offers[0].is_best_offer is True
            assert offers[1].is_best_offer is False

            comparison = calculate_group_comparison(db, groups[0].id)
            assert comparison["offer_count"] == 2
            assert comparison["best_price"] == 77_499.0
            assert comparison["highest_price"] == 79_999.0
            assert comparison["saving_amount"] == 2_500.0

            offer_count_before = db.query(ProductOffer).count()
            history_count_before = db.query(OfferPriceHistory).count()

            teknosa.price = 76_999.0
            teknosa_db.price = teknosa.price
            sync_product_offer(db, teknosa_db, teknosa, price_changed=True)
            db.commit()

            offer_count_after = db.query(ProductOffer).count()
            history_count_after = db.query(OfferPriceHistory).count()
            updated_comparison = calculate_group_comparison(db, groups[0].id)

            assert offer_count_after == offer_count_before
            assert history_count_after == history_count_before + 1
            assert updated_comparison["best_price"] == 76_999.0

            print("ÜRÜN GRUBU SAYISI:", len(groups))
            print("TEKLİF SAYISI:", len(offers))
            print("İLK EN UCUZ FİYAT:", comparison["best_price"])
            print("İLK EN YÜKSEK FİYAT:", comparison["highest_price"])
            print("İLK TASARRUF:", comparison["saving_amount"])
            print("GÜNCEL EN UCUZ FİYAT:", updated_comparison["best_price"])
            print("OFFER ENGINE V2 TESTLERİ BAŞARILI")
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    main()
