from sqlalchemy import inspect, text

from app.database.database import engine


PRODUCT_COLUMNS = {
    "brand": "VARCHAR",
    "model": "VARCHAR",
    "category": "VARCHAR",
    "description": "TEXT",
    "specifications": "TEXT",
    "stock_status": "VARCHAR",
    "source_site": "VARCHAR",
    "product_code": "VARCHAR",
    "last_price_change": "DATETIME",
    "created_at": "DATETIME",
    "updated_at": "DATETIME",
}


def migrate_database() -> None:
    """
    Mevcut SQLite verilerini silmeden eksik sütunları ekler.
    """

    inspector = inspect(engine)

    if "products" not in inspector.get_table_names():
        print(
            "Products tablosu henüz yok. "
            "Migration atlandı."
        )
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("products")
    }

    with engine.begin() as connection:

        for column_name, column_type in PRODUCT_COLUMNS.items():

            if column_name in existing_columns:
                continue

            connection.execute(
                text(
                    f"ALTER TABLE products "
                    f"ADD COLUMN {column_name} {column_type}"
                )
            )

            print(
                f"Yeni veritabanı alanı eklendi: "
                f"{column_name}"
            )

        connection.execute(
            text(
                """
                UPDATE products
                SET stock_status = 'Bilinmiyor'
                WHERE stock_status IS NULL
                """
            )
        )

        connection.execute(
            text(
                """
                UPDATE products
                SET created_at = CURRENT_TIMESTAMP
                WHERE created_at IS NULL
                """
            )
        )

        connection.execute(
            text(
                """
                UPDATE products
                SET updated_at = CURRENT_TIMESTAMP
                WHERE updated_at IS NULL
                """
            )
        )

    print("Veritabanı geçişi tamamlandı.")