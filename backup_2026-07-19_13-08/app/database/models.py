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
)

from app.database.database import Base


# -------------------------
# SQLModel (Scraper Modeli)
# -------------------------

class Product(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)

    name: str

    price: float

    old_price: Optional[float] = None

    rating: Optional[float] = None

    review_count: Optional[int] = None

    seller: str

    url: str

    image: str


# -------------------------
# SQLAlchemy Product Tablosu
# -------------------------

class ProductDB(Base):

    __tablename__ = "products"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String
    )

    price = Column(
        Float
    )

    old_price = Column(
        Float,
        nullable=True
    )

    rating = Column(
        Float,
        nullable=True
    )

    review_count = Column(
        Integer,
        nullable=True
    )

    seller = Column(
        String
    )

    url = Column(
        String,
        unique=True
    )

    image = Column(
        String,
        nullable=True
    )

    ai_score = Column(
        Integer,
        default=0
    )

    last_notified_price = Column(
        Float,
        nullable=True
    )


# -------------------------
# Fiyat Geçmişi
# -------------------------

class PriceHistory(Base):

    __tablename__ = "price_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id")
    )

    price = Column(
        Float
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )