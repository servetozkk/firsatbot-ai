from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
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
# Fiyat Geçmişi
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