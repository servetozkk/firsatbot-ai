from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database.database import Base


# -------------------------
# SQLModel - Scraper Modeli
# -------------------------

class Product(SQLModel, table=True):

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
    )

    name: str

    price: float

    old_price: Optional[float] = None

    rating: Optional[float] = None

    review_count: Optional[int] = None

    seller: str

    url: str

    image: Optional[str] = None

    brand: Optional[str] = None

    model: Optional[str] = None

    category: Optional[str] = None

    description: Optional[str] = None

    specifications: Optional[str] = None

    stock_status: Optional[str] = None

    source_site: Optional[str] = None

    product_code: Optional[str] = None


# -------------------------
# SQLAlchemy Ürün Tablosu
# -------------------------

class ProductDB(Base):

    __tablename__ = "products"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    price = Column(
        Float,
        nullable=False,
    )

    old_price = Column(
        Float,
        nullable=True,
    )

    rating = Column(
        Float,
        nullable=True,
    )

    review_count = Column(
        Integer,
        nullable=True,
    )

    seller = Column(
        String,
        nullable=True,
    )

    url = Column(
        String,
        unique=True,
        nullable=False,
    )

    image = Column(
        String,
        nullable=True,
    )

    ai_score = Column(
        Integer,
        default=0,
        nullable=False,
    )

    last_notified_price = Column(
        Float,
        nullable=True,
    )

    # -------------------------
    # Ürün Detay Alanları
    # -------------------------

    brand = Column(
        String,
        nullable=True,
    )

    model = Column(
        String,
        nullable=True,
    )

    category = Column(
        String,
        nullable=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    specifications = Column(
        Text,
        nullable=True,
    )

    stock_status = Column(
        String,
        nullable=True,
        default="Bilinmiyor",
    )

    source_site = Column(
        String,
        nullable=True,
    )

    product_code = Column(
        String,
        nullable=True,
    )

    last_price_change = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Eski Fiyat Geçmişi
# -------------------------

class PriceHistory(Base):

    __tablename__ = "price_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True,
    )

    price = Column(
        Float,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Mağazalar
# -------------------------

class Store(Base):

    __tablename__ = "stores"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    code = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    base_url = Column(
        String,
        nullable=True,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Ortak Ürün Grubu
# -------------------------

class ProductGroup(Base):

    __tablename__ = "product_groups"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    group_key = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    canonical_name = Column(
        String,
        nullable=False,
    )

    normalized_name = Column(
        String,
        nullable=False,
        index=True,
    )

    brand = Column(
        String,
        nullable=True,
        index=True,
    )

    model = Column(
        String,
        nullable=True,
        index=True,
    )

    category = Column(
        String,
        nullable=True,
        index=True,
    )

    image = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Mağaza Teklifleri
# -------------------------

class ProductOffer(Base):

    __tablename__ = "product_offers"

    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "store_product_id",
            name="uq_offer_store_product",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    group_id = Column(
        Integer,
        ForeignKey("product_groups.id"),
        nullable=False,
        index=True,
    )

    store_id = Column(
        Integer,
        ForeignKey("stores.id"),
        nullable=False,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    store_product_id = Column(
        String,
        nullable=True,
        index=True,
    )

    seller = Column(
        String,
        nullable=True,
    )

    url = Column(
        String,
        unique=True,
        nullable=False,
    )

    current_price = Column(
        Float,
        nullable=False,
    )

    old_price = Column(
        Float,
        nullable=True,
    )

    shipping_price = Column(
        Float,
        nullable=True,
    )

    availability = Column(
        String,
        default="Bilinmiyor",
        nullable=False,
    )

    rating = Column(
        Float,
        nullable=True,
    )

    review_count = Column(
        Integer,
        nullable=True,
    )

    is_best_offer = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    last_checked_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Teklif Fiyat Geçmişi
# -------------------------

class OfferPriceHistory(Base):

    __tablename__ = "offer_price_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    offer_id = Column(
        Integer,
        ForeignKey("product_offers.id"),
        nullable=False,
        index=True,
    )

    price = Column(
        Float,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )