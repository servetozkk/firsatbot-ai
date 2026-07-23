from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
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
    from app.database.models import (
        ProductDB,
        PriceHistory,
    )

    Base.metadata.create_all(bind=engine)

    from app.database.migrations import migrate_database

    migrate_database()