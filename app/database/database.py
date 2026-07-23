from sqlalchemy import create_engine
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)


DATABASE_URL = "sqlite:///data/products.db"


engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False,
    },
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()


def create_db() -> None:
    """
    Uygulamanın kullandığı bütün SQLAlchemy
    tablolarını oluşturur.

    create_all mevcut tabloları veya verileri silmez.
    Sadece bulunmayan tabloları oluşturur.
    """

    from app.database.models import (
        OfferPriceHistory,
        PriceHistory,
        ProductDB,
        ProductGroup,
        ProductOffer,
        Store,
    )

    Base.metadata.create_all(
        bind=engine,
    )

    from app.database.migrations import migrate_database

    migrate_database()